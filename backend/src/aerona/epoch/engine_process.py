import asyncio
import multiprocessing
import os
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from typing import Any
from weakref import WeakKeyDictionary

from aerona.core.errors import AeronaError
from aerona.db.session import Database, SharedGate, WriteGate, shared_gate
from aerona.domain.enums.epoch import EngineStage
from aerona.engine.context import Publisher, TickEnvironment
from aerona.engine.parallel.pool import exit_with_parent
from aerona.engine.phase import Phase
from aerona.engine.pipeline import EnginePhaseError, all_phases
from aerona.engine.stats import TickStats
from aerona.epoch.engine_stage import StageRun, engine_stage
from aerona.events.kinds import EventKind

EVENT = "event"
REPORT = "report"
CHILD: dict[str, Any] = {}


def silent(_kind: EventKind, _payload: dict[str, Any]) -> None:
    return None


@dataclass(frozen=True)
class StageOrder:
    url: str
    epoch: int
    stage: EngineStage
    phases: tuple[str | Phase, ...]
    environment: TickEnvironment
    tolerant: frozenset[str]


@dataclass(frozen=True)
class StageOutcome:
    stats: TickStats
    failure: str | None = None
    phase: str | None = None


def portable(phases: tuple[Phase, ...]) -> tuple[str | Phase, ...]:
    known = {phase.name: phase.run for phase in all_phases()}
    return tuple(phase.name if known.get(phase.name) is phase.run else phase for phase in phases)


def resolved(phases: tuple[str | Phase, ...]) -> tuple[Phase, ...]:
    known = {phase.name: phase for phase in all_phases()}
    return tuple(known[phase] if isinstance(phase, str) else phase for phase in phases)


def absorb(target: TickStats, source: TickStats) -> None:
    target.counters.update(source.counters)
    target.phase_seconds.update(source.phase_seconds)
    target.phase_cpu.update(source.phase_cpu)
    target.flows.update(source.flows)
    target.grants.update(source.grants)


def child_start(parent: int, shared: SharedGate, outbox: Any) -> None:
    exit_with_parent(parent)
    CHILD["shared"] = shared
    CHILD["outbox"] = outbox


def child_publish(kind: EventKind, payload: dict[str, Any]) -> None:
    CHILD["outbox"].put((EVENT, kind.value, payload))


def child_report(message: str) -> None:
    CHILD["outbox"].put((REPORT, message, {}))


def stage_in_child(order: StageOrder) -> StageOutcome:
    shared: SharedGate = CHILD["shared"]

    async def run() -> StageOutcome:
        database = Database(order.url, WriteGate(shared, yielding=True))
        environment = replace(order.environment, publish=child_publish)
        try:
            await engine_stage(database, StageRun(order.epoch, order.stage, resolved(order.phases), environment, order.tolerant, child_report, shared.stop))
        except EnginePhaseError as error:
            return StageOutcome(environment.stats, str(error.__cause__ or error.message), error.phase)
        except AeronaError as error:
            return StageOutcome(environment.stats, error.message)
        finally:
            await database.close()
        return StageOutcome(environment.stats)

    return asyncio.run(run())


def job_in_child[T](url: str, job: Callable[[Database, Publisher], Awaitable[T]]) -> T:
    shared: SharedGate = CHILD["shared"]

    async def run() -> T:
        database = Database(url, WriteGate(shared, yielding=True))
        try:
            return await job(database, child_publish)
        finally:
            await database.close()

    return asyncio.run(run())


class EngineProcess:
    def __init__(self, database: Database) -> None:
        context = multiprocessing.get_context("spawn")
        self.shared = shared_gate()
        self.outbox = context.Queue()
        self.pool = ProcessPoolExecutor(max_workers=1, mp_context=context, initializer=child_start, initargs=(os.getpid(), self.shared, self.outbox))
        self.database = database
        self._deliver: Callable[[tuple[str, str, dict[str, Any]]], None] | None = None
        self._lock = asyncio.Lock()
        self._shared = False
        threading.Thread(target=self._read, daemon=True, name="engine-events").start()

    def _read(self) -> None:
        while True:
            message = self.outbox.get()
            if message is None:
                return
            deliver = self._deliver
            if deliver is not None:
                deliver(message)

    async def _share(self) -> None:
        if self._shared:
            return
        gate = self.database.gate
        await gate.acquire()
        try:
            gate.share(self.shared)
        finally:
            gate.release()
        self._shared = True

    async def run(self, order: StageOrder, publish: Publisher, report: Callable[[str], None]) -> StageOutcome:
        return await self.call(publish, report, stage_in_child, order)

    async def call[T](self, publish: Publisher, report: Callable[[str], None], work: Callable[..., T], *args: object) -> T:
        async with self._lock:
            await self._share()
            loop = asyncio.get_running_loop()

            def handle(message: tuple[str, str, dict[str, Any]]) -> None:
                kind, text, payload = message
                if kind == EVENT:
                    publish(EventKind(text), payload)
                else:
                    report(text)

            def deliver(message: tuple[str, str, dict[str, Any]]) -> None:
                loop.call_soon_threadsafe(handle, message)

            self._deliver = deliver
            self.shared.stop.clear()
            future = loop.run_in_executor(self.pool, work, *args)
            try:
                return await asyncio.shield(future)
            except asyncio.CancelledError:
                self.shared.stop.set()
                await asyncio.wait({future})
                raise

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.outbox.put(None)


PROCESSES: WeakKeyDictionary[Database, EngineProcess] = WeakKeyDictionary()


def engine_process_of(database: Database) -> EngineProcess:
    found = PROCESSES.get(database)
    if found is None:
        found = PROCESSES[database] = EngineProcess(database)
    return found


def close_engine_process(database: Database) -> None:
    found = PROCESSES.pop(database, None)
    if found is not None:
        found.close()


async def job_in_process[T](database: Database, job: Callable[[Database, Publisher], Awaitable[T]], publish: Publisher) -> T:
    return await engine_process_of(database).call(publish, lambda _message: None, job_in_child, database.url, job)


async def stage_in_process(database: Database, order: StageOrder, environment: TickEnvironment, report: Callable[[str], None]) -> None:
    outcome = await engine_process_of(database).run(replace(order, environment=replace(environment, publish=silent)), environment.publish, report)
    absorb(environment.stats, outcome.stats)
    if outcome.failure is not None:
        if outcome.phase is not None:
            raise EnginePhaseError(outcome.phase, RuntimeError(outcome.failure))
        raise AeronaError(outcome.failure)
