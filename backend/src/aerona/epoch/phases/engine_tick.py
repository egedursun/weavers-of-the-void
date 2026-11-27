import asyncio
import logging
import time
from collections.abc import Sequence

from sqlalchemy import select

from aerona.core.errors import AeronaError
from aerona.db.session import Steps
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.epoch import EngineStage, EpochPhase
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.engine.context import TickContext, TickEnvironment, at_step
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.notes import fold_tick_lines, last_chronicle_id
from aerona.engine.phase import Phase
from aerona.engine.pipeline import (
    DISABLED_COUNTER,
    FAILED_COUNTER,
    TICK_ORDER,
    EnginePhaseError,
    current_environment,
    disabled_by_rules,
    warn_over_budget,
)
from aerona.epoch.context import EpochContext
from aerona.epoch.state import engine_phases_done, mark_engine_phase, raise_phase, require_run
from aerona.events.kinds import EventKind

LOGGER = logging.getLogger(__name__)


async def run_engine_stage(
    ec: EpochContext,
    stage: EngineStage,
    phases: Sequence[Phase],
    environment: TickEnvironment,
    tolerant: frozenset[str] = frozenset(),
) -> None:
    async with ec.database.read() as session:
        done = await engine_phases_done(session, ec.epoch, stage)
    disabled = disabled_by_rules(environment.rules)
    async with ec.database.steps() as steps:
        for index, phase in enumerate(phases):
            if phase.name in done:
                continue
            if phase.name in disabled:
                environment.stats.count(f"{phase.name}.{DISABLED_COUNTER}")
                continue
            try:
                await run_engine_phase(ec, stage, phase, at_step(environment, index, len(phases)), steps)
            except AeronaError as error:
                if phase.name not in tolerant:
                    raise
                LOGGER.exception("Engine step %s failed and was skipped", phase.name)
                environment.stats.count(f"{phase.name}.{FAILED_COUNTER}")
                ec.runtime.error(f"Engine step {phase.name}: {error.message}")


async def run_engine_phase(ec: EpochContext, stage: EngineStage, phase: Phase, environment: TickEnvironment, steps: Steps) -> None:
    started = time.perf_counter()
    try:
        async with steps.step() as session:
            await run_guarded(phase, TickContext(environment, session, phase.name))
            await mark_engine_phase(session, ec.epoch, stage, phase.name, time.perf_counter() - started)
    except AeronaError:
        raise
    except Exception as error:
        raise EnginePhaseError(phase.name, error) from error
    seconds = time.perf_counter() - started
    environment.stats.phase_seconds[phase.name] = environment.stats.phase_seconds.get(phase.name, 0.0) + seconds
    environment.publish(EventKind.ENGINE_PHASE, {"epoch": ec.epoch, "phase": phase.name, "seconds": seconds})
    await asyncio.sleep(0)


async def engine_tick(ec: EpochContext, phases: Sequence[Phase] | None = None) -> None:
    async with ec.database.write() as session:
        run = await require_run(session, ec.epoch)
        if run.phase >= EpochPhase.ENGINE:
            ec.engine_notes = list(run.engine_notes)
            return
        if run.engine_since_chronicle_id is None:
            run.engine_since_chronicle_id = await last_chronicle_id(session)
        since = run.engine_since_chronicle_id
    async with ec.database.read() as session:
        ec.sleeping_gods = set(await session.scalars(select(ForeignGodRow.id).where(ForeignGodRow.status == ForeignGodStatus.ASLEEP)))
    await ec.enter_phase(EpochPhase.ENGINE)
    ec.publish(EventKind.ENGINE_STARTED, {})
    environment = await current_environment(ec.database, ec.runtime.publish, phase=EpochPhase.ENGINE)
    await run_engine_stage(ec, EngineStage.TICK, phases if phases is not None else TICK_ORDER, environment)
    over = warn_over_budget(environment)
    if over is not None:
        target = environment.rules.engine_budget.tick_target_seconds
        ec.runtime.note(
            f"The world's course took {over:.0f} seconds this epoch, over its {target}-second target; "
            "raise the target or lower the sub-step budget in World Rules."
        )
    async with ec.database.write() as session:
        rules = await ec.runtime.rules(session)
        await fold_tick_lines(session, rules, ec.epoch, since)
        rows = await session.scalars(
            select(ChronicleRow.text).where(ChronicleRow.epoch == ec.epoch, ChronicleRow.id > since, ChronicleRow.visible.is_(True)).order_by(ChronicleRow.id)
        )
        notes = list(rows)
        run = await require_run(session, ec.epoch)
        run.engine_notes = notes
        await raise_phase(session, ec.epoch, EpochPhase.ENGINE)
    ec.engine_notes = notes
    ec.summary["engine_notes"] = len(notes)
    if ec.hooks.after_tick is not None:
        try:
            await ec.hooks.after_tick(ec.epoch, since)
        except Exception as error:
            LOGGER.exception("After-tick hook failed")
            ec.runtime.error(f"After the world's course: {error}")
    ec.publish(EventKind.ENGINE_FINISHED, {"notes": len(notes)})
    await ec.complete_phase(EpochPhase.ENGINE)
    ec.checkpoint(int(EpochPhase.ENGINE))
