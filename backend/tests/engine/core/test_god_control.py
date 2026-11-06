import traceback
from collections import Counter
from collections.abc import Callable
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import ORMExecuteState, Session, object_mapper

from aerona.db.base import Base
from aerona.db.profile_guard import owned_shape, owner_ids, profile_mapper
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.pipeline import all_phases, current_environment, simulate
from tests.engine.integration.factories import seed_rich_cosmos

BLOCK_EVERY_NODE = -1
WARM_EPOCHS = 2
ENGINE_MARK = "/aerona/engine/"
HELPER_MARKS = ("/engine/notes.py", "/engine/context.py", "/engine/primitives/", "/engine/interconnect/guards.py")


def table_of(row: object) -> str:
    return str(getattr(type(row), "__tablename__", type(row).__name__))


def tied_to_a_node(row: object) -> bool:
    shape = owned_shape(object_mapper(row))
    return shape is not None and bool(owner_ids(row, shape))


def owned_table(name: str) -> bool:
    mapper = profile_mapper(name)
    return mapper is not None and owned_shape(mapper) is not None


def origin() -> str:
    frames = [frame for frame in traceback.extract_stack() if ENGINE_MARK in frame.filename and not any(mark in frame.filename for mark in HELPER_MARKS)]
    return " > ".join(f"{frame.filename.split(ENGINE_MARK)[-1]}:{frame.lineno}:{frame.name}" for frame in frames[-3:]) or "?"


class Watcher:
    def __init__(self) -> None:
        self.changes: Counter[str] = Counter()
        self.origins: dict[int, str] = {}

    def pending(self, _session: Session, row: object) -> None:
        self.origins[id(row)] = origin()

    def after_flush(self, session: Session, _context: object) -> None:
        for row in session.new:
            if tied_to_a_node(row):
                self.changes[f"created {table_of(row)} at {self.origins.get(id(row), '?')}"] += 1
        for row in session.deleted:
            if tied_to_a_node(row):
                self.changes[f"deleted {table_of(row)}"] += 1
        for row in session.dirty:
            if tied_to_a_node(row):
                for attribute in inspect(row).attrs:
                    if attribute.history.has_changes():
                        self.changes[f"changed {table_of(row)}.{attribute.key}"] += 1

    def statement(self, state: ORMExecuteState) -> Any:
        if not (state.is_insert or state.is_update or state.is_delete):
            return None
        result = state.invoke_statement()
        table = getattr(getattr(state.statement, "table", None), "name", "")
        if getattr(result, "rowcount", 0) and owned_table(table):
            self.changes[f"bulk write to {table} at {origin()}"] += 1
        return result


async def run_watched(database: Database, phase_name: str, only: int) -> tuple[Counter[str], str | None]:
    phase = next(item for item in all_phases() if item.name == phase_name)
    environment = await current_environment(database)
    watcher = Watcher()
    listeners: list[tuple[str, Callable[..., Any]]] = [
        ("transient_to_pending", watcher.pending),
        ("after_flush", watcher.after_flush),
        ("do_orm_execute", watcher.statement),
    ]
    error: str | None = None
    async with database.write() as session:
        nested = await session.begin_nested()
        for name, listener in listeners:
            event.listen(session.sync_session, name, listener)
        try:
            await run_guarded(phase, TickContext(environment, session, phase.name), only=only)
            await session.flush()
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
        finally:
            for name, listener in listeners:
                event.remove(session.sync_session, name, listener)
            await nested.rollback()
            await session.rollback()
    return watcher.changes, error


async def test_every_engine_step_obeys_a_hold_and_runs_when_forced_on_one_node(database: Database) -> None:
    async with database.write() as session:
        await seed_rich_cosmos(session)
    await simulate(database, WARM_EPOCHS)
    async with database.read() as session:
        target = await session.scalar(
            select(EntityRow.id).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    assert target is not None and Base.metadata.tables
    disobeyed: dict[str, list[str]] = {}
    broken: dict[str, str] = {}
    for phase in all_phases():
        changes, error = await run_watched(database, phase.name, BLOCK_EVERY_NODE)
        if changes:
            disobeyed[phase.name] = [f"{count}x {change}" for change, count in changes.most_common()]
        if error is not None:
            broken[f"{phase.name} held"] = error
        _, forced = await run_watched(database, phase.name, target)
        if forced is not None:
            broken[f"{phase.name} forced"] = forced
    assert broken == {}, "\n".join(f"{name}: {error}" for name, error in broken.items())
    assert disobeyed == {}, "Engine steps that still act on held nodes; skip held nodes where they choose whom to act on:\n" + "\n".join(
        f"{name}: {'; '.join(lines)}" for name, lines in disobeyed.items()
    )
