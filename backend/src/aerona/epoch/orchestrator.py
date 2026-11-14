from dataclasses import dataclass, field
from typing import Any

from aerona.agents.fate.naming import name_pending_records
from aerona.agents.metrics import metrics_epoch
from aerona.agents.runtime import AgentRuntime
from aerona.agents.son import SonTurnResult, run_son_turn
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP, EpochStoppedError, StopSignal
from aerona.epoch.context import EpochContext
from aerona.epoch.phases.auto_council import auto_council
from aerona.epoch.phases.backup import take_backup
from aerona.epoch.phases.deferred import deferred_worlds, launch_background
from aerona.epoch.phases.distribution import distribute_sons
from aerona.epoch.phases.engine_tick import engine_tick
from aerona.epoch.phases.fate import fate_and_chronicle
from aerona.epoch.phases.finalize import close_epoch, localise, network_rule_repair, prune
from aerona.epoch.phases.image_autogen import image_autogen
from aerona.epoch.phases.mortal_turns import mortal_turns
from aerona.epoch.phases.son_turns import son_turns
from aerona.epoch.phases.start import complete_missing
from aerona.epoch.phases.transition import transition
from aerona.epoch.phases.voices import voices
from aerona.epoch.ports import EpochHooks
from aerona.epoch.resume import begin_run, requeue_intuitions, stale_runs
from aerona.epoch.state import require_run
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager


@dataclass(frozen=True)
class EpochReport:
    epoch: int
    stopped: bool = False
    phase: int = 0
    summary: dict[str, Any] = field(default_factory=dict)

    def as_result(self) -> dict[str, Any]:
        return {"epoch": self.epoch, "stopped": self.stopped, "phase": self.phase, "summary": self.summary}


class EpochOrchestrator:
    def __init__(self, runtime: AgentRuntime, jobs: JobManager | None = None, hooks: EpochHooks | None = None) -> None:
        self.runtime = runtime
        self.jobs = jobs
        self.hooks = hooks or EpochHooks()
        self.stop = StopSignal()

    async def recover(self) -> int:
        async with self.runtime.database.write() as session:
            return await requeue_intuitions(session)

    def request_stop(self) -> None:
        self.stop.request()
        self.runtime.publish(EventKind.EPOCH_STOP_REQUESTED, {})
        self.runtime.note("The epoch will be stopped once the current step finishes; it can be resumed afterwards.")

    async def submit(self) -> str:
        if self.jobs is None:
            raise ValidationFailedError("No job manager is available.")
        await self.require_world()
        return await self.jobs.submit(JobKind.EPOCH, self.handler, exclusive_group=WORLD_GROUP)

    async def submit_son_turn(self, son_id: int) -> str:
        if self.jobs is None:
            raise ValidationFailedError("No job manager is available.")

        async def handler(_job: JobContext) -> dict[str, Any]:
            result = await self.act_son(son_id)
            return {"son_id": result.son_id, "word": result.word, "creations": result.creations, "status": result.status}

        return await self.jobs.submit(JobKind.SON_TURN, handler, {"son_id": son_id}, exclusive_group=WORLD_GROUP)

    async def submit_naming(self) -> str:
        if self.jobs is None:
            raise ValidationFailedError("No job manager is available.")

        async def handler(_job: JobContext) -> dict[str, Any]:
            report = await name_pending_records(self.runtime)
            return {"named": report.named, "left": report.left}

        return await self.jobs.submit(JobKind.NAMING, handler, exclusive_group=WORLD_GROUP)

    async def act_son(self, son_id: int) -> SonTurnResult:
        return await run_son_turn(self.runtime, son_id)

    async def handler(self, job: JobContext) -> dict[str, Any]:
        return (await self.run(job)).as_result()

    async def require_world(self) -> None:
        async with self.runtime.database.read() as session:
            if await CosmosRepository(session).get() is None:
                raise ValidationFailedError("No world.")

    async def settle_stale_runs(self, job: JobContext | None) -> None:
        async with self.runtime.database.read() as session:
            stale = [run.epoch for run in await stale_runs(session)]
        for epoch in stale:
            with metrics_epoch(epoch):
                await self.after_transition(EpochContext(self.runtime, self.hooks, self.stop, epoch, resuming=True, job=job))

    async def run(self, job: JobContext | None = None) -> EpochReport:
        await self.require_world()
        self.stop.clear()
        await self.settle_stale_runs(job)
        async with self.runtime.database.write() as session:
            start = await begin_run(session)
        ec = EpochContext(self.runtime, self.hooks, self.stop, start.epoch, start.resuming, job)
        with metrics_epoch(start.epoch):
            return await self.run_epoch(ec, start.phase)

    async def run_epoch(self, ec: EpochContext, phase: int) -> EpochReport:
        if ec.resuming:
            ec.publish(EventKind.EPOCH_RESUMED, {"phase": phase})
            self.runtime.note(f"Epoch {ec.epoch} was left half-done; everything after phase {several(phase, 'continue', 'continues')} where it stopped.")
        try:
            await self.before_transition(ec)
        except EpochStoppedError as stopped:
            ec.publish(EventKind.EPOCH_STOPPED, {"phase": stopped.phase})
            self.runtime.note(f"Epoch {ec.epoch} stopped after phase {stopped.phase}. Completing the epoch resumes it.")
            return EpochReport(ec.epoch, stopped=True, phase=stopped.phase, summary=ec.summary)
        finally:
            self.stop.clear()
        await transition(ec)
        await self.after_transition(ec)
        return EpochReport(ec.epoch, phase=int(EpochPhase.TRANSITION), summary=ec.summary)

    async def before_transition(self, ec: EpochContext) -> None:
        await complete_missing(ec)
        await take_backup(ec)
        await distribute_sons(ec)
        await son_turns(ec)
        await mortal_turns(ec)
        await engine_tick(ec)
        async with ec.database.read() as session:
            fate_done = (await require_run(session, ec.epoch)).phase >= EpochPhase.FATE
        if not fate_done:
            await fate_and_chronicle(ec)
            await voices(ec)
            await auto_council(ec)
            await ec.complete_phase(EpochPhase.FATE)
        ec.checkpoint(int(EpochPhase.FATE))

    async def after_transition(self, ec: EpochContext) -> None:
        await deferred_worlds(ec)
        await network_rule_repair(ec)
        await localise(ec)
        await prune(ec)
        await close_epoch(ec)
        await launch_background(ec)
        await image_autogen(ec)
