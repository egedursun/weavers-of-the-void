from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sqlalchemy import event, func, select
from sqlalchemy.orm import ORMExecuteState, Session
from sqlalchemy.orm.base import instance_state

from aerona.db.attr_history import history_of
from aerona.db.ledger_capture import UNCAPTURED_TABLES, key_text, mapper_plans, state_key
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.pipeline import all_phases, current_environment, simulate
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

WARM_EPOCHS = 2
BULK = "*bulk*"
Written = tuple[str, str, str | None]


class Expectation:
    def __init__(self) -> None:
        self.written: set[Written] = set()
        self.rebuilt: set[str] = set()

    def after_flush(self, session: Session, _context: object) -> None:
        for instance in session.new:
            state = instance_state(instance)
            self.written.update((plan.name, key_text(state_key(plan, state)), None) for plan in mapper_plans(state.mapper))
        for instance in session.deleted:
            state = instance_state(instance)
            self.written.update((plan.name, key_text(state_key(plan, state)), None) for plan in mapper_plans(state.mapper))
        for instance in session.dirty:
            state = instance_state(instance)
            for plan in mapper_plans(state.mapper):
                for column in plan.columns:
                    history = history_of(state, column.key)
                    if history.added and history.deleted and history.added[0] != history.deleted[0]:
                        self.written.add((plan.name, key_text(state_key(plan, state)), column.name))

    def statement(self, state: ORMExecuteState) -> Any:
        if not (state.is_insert or state.is_update or state.is_delete):
            return None
        result = state.invoke_statement()
        table = getattr(getattr(state.statement, "table", None), "name", "")
        if state.is_delete and getattr(state.statement, "whereclause", None) is None:
            self.rebuilt.add(table)
        if getattr(result, "rowcount", 0) and table and table not in UNCAPTURED_TABLES:
            self.written.add((table, BULK, None))
        return result


async def recorded_gaps(database: Database, phase_name: str) -> tuple[list[str], str | None]:
    phase = next(item for item in all_phases() if item.name == phase_name)
    environment = replace(await current_environment(database), rules=eager((await current_environment(database)).rules))
    expectation = Expectation()
    listeners: list[tuple[str, Callable[..., Any]]] = [("after_flush", expectation.after_flush), ("do_orm_execute", expectation.statement)]
    error: str | None = None
    gaps: list[str] = []
    async with database.write() as session:
        nested = await session.begin_nested()
        mark = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
        for name, listener in listeners:
            event.listen(session.sync_session, name, listener)
        try:
            await run_guarded(phase, TickContext(environment, session, phase.name))
            await session.flush()
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
        finally:
            for name, listener in listeners:
                event.remove(session.sync_session, name, listener)
        rows = (
            await session.execute(
                select(StateChangeRow.table_name, StateChangeRow.row_key, StateChangeRow.field, StateChangeRow.incident_id).where(StateChangeRow.id > mark)
            )
        ).all()
        recorded = {(table, key, field) for table, key, field, _ in rows}
        tables = {table for table, _, _, _ in rows}
        unattributed = sum(1 for *_, incident in rows if incident is None)
        written = {item for item in expectation.written if item[0] not in expectation.rebuilt}
        missing = sorted(item for item in written if (item[0] not in tables if item[1] == BULK else item not in recorded))
        gaps = [f"{table} {key} {field or 'row'}" for table, key, field in missing[:20]]
        if unattributed:
            gaps.append(f"{unattributed} change(s) belong to no happening")
        await nested.rollback()
        await session.rollback()
    return gaps, error


async def test_every_write_of_every_engine_step_leaves_a_change_tied_to_a_happening(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, WARM_EPOCHS)
    unrecorded: dict[str, list[str]] = {}
    broken: dict[str, str] = {}
    for phase in all_phases():
        gaps, error = await recorded_gaps(database, phase.name)
        if gaps:
            unrecorded[phase.name] = gaps
        if error is not None:
            broken[phase.name] = error
    assert broken == {}, "\n".join(f"{name}: {error}" for name, error in broken.items())
    assert unrecorded == {}, "Engine writes left without a recorded change:\n" + "\n".join(f"{name}: {'; '.join(lines)}" for name, lines in unrecorded.items())
