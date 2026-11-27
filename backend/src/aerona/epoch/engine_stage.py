import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from aerona.core.errors import AeronaError
from aerona.db.session import Database, Steps
from aerona.domain.enums.epoch import EngineStage
from aerona.engine.context import TickContext, TickEnvironment, at_step
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.pipeline import DISABLED_COUNTER, FAILED_COUNTER, EnginePhaseError, disabled_by_rules
from aerona.epoch.state import engine_phases_done, mark_engine_phase
from aerona.events.kinds import EventKind

LOGGER = logging.getLogger(__name__)


class Stopping(Protocol):
    def is_set(self) -> bool: ...


@dataclass(frozen=True)
class StageRun:
    epoch: int
    stage: EngineStage
    phases: tuple[Phase, ...]
    environment: TickEnvironment
    tolerant: frozenset[str]
    report: Callable[[str], None]
    stop: Stopping


async def engine_stage(database: Database, run: StageRun) -> None:
    epoch, stage, environment = run.epoch, run.stage, run.environment
    async with database.read() as session:
        done = await engine_phases_done(session, epoch, stage)
    disabled = disabled_by_rules(environment.rules)
    async with database.steps() as steps:
        for index, phase in enumerate(run.phases):
            if run.stop.is_set():
                return
            if phase.name in done:
                continue
            if phase.name in disabled:
                environment.stats.count(f"{phase.name}.{DISABLED_COUNTER}")
                continue
            try:
                await run_engine_phase(epoch, stage, phase, at_step(environment, index, len(run.phases)), steps)
            except AeronaError as error:
                if phase.name not in run.tolerant:
                    raise
                LOGGER.exception("Engine step %s failed and was skipped", phase.name)
                environment.stats.count(f"{phase.name}.{FAILED_COUNTER}")
                run.report(f"Engine step {phase.name}: {error.message}")


async def run_engine_phase(epoch: int, stage: EngineStage, phase: Phase, environment: TickEnvironment, steps: Steps) -> None:
    started = time.perf_counter()
    try:
        async with steps.step() as session:
            await run_guarded(phase, TickContext(environment, session, phase.name))
            await mark_engine_phase(session, epoch, stage, phase.name, time.perf_counter() - started)
    except AeronaError:
        raise
    except Exception as error:
        raise EnginePhaseError(phase.name, error) from error
    seconds = time.perf_counter() - started
    environment.stats.phase_seconds[phase.name] = environment.stats.phase_seconds.get(phase.name, 0.0) + seconds
    environment.publish(EventKind.ENGINE_PHASE, {"epoch": epoch, "phase": phase.name, "seconds": seconds})
    await asyncio.sleep(0)
