import asyncio
import logging
import threading
from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy import select

from aerona.db.off_loop import ENGINE_THREADS, off_loop, threadsafe
from aerona.db.session import Database
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.epoch import EngineStage, EpochPhase
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.engine.context import TickEnvironment
from aerona.engine.notes import fold_tick_lines, last_chronicle_id
from aerona.engine.phase import Phase
from aerona.engine.pipeline import TICK_ORDER, current_environment, warn_over_budget
from aerona.epoch.context import EpochContext
from aerona.epoch.engine_process import StageOrder, portable, stage_in_process
from aerona.epoch.engine_stage import StageRun, engine_stage
from aerona.epoch.state import raise_phase, require_run
from aerona.events.kinds import EventKind

LOGGER = logging.getLogger(__name__)


async def run_engine_stage(
    ec: EpochContext,
    stage: EngineStage,
    phases: Sequence[Phase],
    environment: TickEnvironment,
    tolerant: frozenset[str] = frozenset(),
) -> None:
    loop = asyncio.get_running_loop()
    report = threadsafe(loop, ec.runtime.error)
    if ec.database.work_in_processes:
        order = StageOrder(ec.database.url, ec.epoch, stage, portable(tuple(phases)), environment, tolerant)
        await stage_in_process(ec.database, order, environment, report)
        return
    threaded = replace(environment, publish=threadsafe(loop, environment.publish))

    async def work(database: Database, stop: threading.Event) -> None:
        await engine_stage(database, StageRun(ec.epoch, stage, tuple(phases), threaded, tolerant, report, stop))

    await off_loop(ec.database, work, ENGINE_THREADS)


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
