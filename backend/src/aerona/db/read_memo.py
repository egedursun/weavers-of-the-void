from collections.abc import Awaitable, Callable, Hashable, Iterable
from dataclasses import dataclass, field
from typing import Any, Concatenate

from sqlalchemy import Table, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstanceState, ORMExecuteState, Session
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ClauseElement

MEMO_KEY = "aerona.read_memo"
FLUSHING_KEY = "aerona.read_memo.flushing"
PENDING_KEY = "aerona.read_memo.pending"
KEEP_KEY = "aerona.read_memo.keep"
EVERY_TABLE: frozenset[str] = frozenset()
STRUCTURAL: dict[str, frozenset[str]] = {"entities": frozenset({"entity_type", "status", "location_id", "world_id", "creator_son_id"})}


@dataclass
class Memo:
    tables: frozenset[str]
    values: dict[Hashable, Any] = field(default_factory=dict)

    def touched_by(self, changed: set[str] | None) -> bool:
        return changed is None or not self.tables or not self.tables.isdisjoint(changed)


def with_parts(name: str) -> set[str]:
    return {name, f"{name}.other"} if name in STRUCTURAL else {name}


def table_names(tables: Iterable[Any]) -> frozenset[str]:
    return frozenset(getattr(table, "__tablename__", None) or str(table) for table in tables)


def changed_tables(state: InstanceState[Any], whole: bool) -> set[str]:
    found: set[str] = set()
    for table in state.mapper.tables:
        if not isinstance(table, Table):
            continue
        watched = STRUCTURAL.get(table.name)
        if watched is None or whole or not watched.isdisjoint(state.committed_state):
            found.add(table.name)
        if watched is not None:
            found.add(f"{table.name}.other")
    return found


def state_tables(states: Iterable[InstanceState[Any]], whole: bool = True) -> set[str]:
    return {name for state in states for name in changed_tables(state, whole)}


def pending_tables(sync: Session) -> set[str]:
    modified = sync.identity_map._modified
    if not sync._new and not sync._deleted and not modified:
        return set()
    signature = (len(sync._new), len(sync._deleted), len(modified))
    cached: tuple[tuple[int, int, int], set[str]] | None = sync.info.get(PENDING_KEY)
    if cached is not None and cached[0] == signature:
        return cached[1]
    found = state_tables([*sync._new, *sync._deleted, *modified])
    sync.info[PENDING_KEY] = (signature, found)
    return found


def memos(sync: Session) -> dict[str, Memo]:
    found: dict[str, Memo] = sync.info.setdefault(MEMO_KEY, {})
    return found


def memo_for(sync: Session, name: str, tables: frozenset[str] = EVERY_TABLE) -> dict[Hashable, Any] | None:
    pending = pending_tables(sync)
    if pending and (not tables or not tables.isdisjoint(pending)):
        return None
    table = memos(sync)
    memo = table.get(name)
    if memo is None:
        memo = table[name] = Memo(tables)
    return memo.values


def memo_of(session: AsyncSession, name: str, tables: frozenset[str] = EVERY_TABLE) -> dict[Hashable, Any] | None:
    return memo_for(session.sync_session, name, tables)


def forget(sync: Session, changed: set[str] | None) -> None:
    sync.info.pop(PENDING_KEY, None)
    table = memos(sync)
    for name in [name for name, memo in table.items() if memo.touched_by(changed)]:
        del table[name]


def flushing_tables(sync: Session) -> set[str]:
    return state_tables([*sync._new, *sync._deleted]) | state_tables(sync.identity_map._modified, whole=False)


def note_flushing(sync: Session, *_: object) -> None:
    sync.info[FLUSHING_KEY] = flushing_tables(sync)


def forget_flushed(sync: Session, *_: object) -> None:
    captured: set[str] = sync.info.pop(FLUSHING_KEY, set())
    forget(sync, captured | flushing_tables(sync))


SESSION_INDEXES: list[str] = []


def register_index(key: str) -> None:
    if key not in SESSION_INDEXES:
        SESSION_INDEXES.append(key)


def forget_all(sync: Session, *_: object) -> None:
    forget(sync, None)
    for key in SESSION_INDEXES:
        sync.info.pop(key, None)


def forget_on_write(state: ORMExecuteState) -> None:
    if state.is_select:
        return
    target = getattr(state.statement, "table", None)
    forget(state.session, with_parts(target.name) if isinstance(target, Table) else None)


def keep(sync: Session, instance: object) -> None:
    kept: list[object] | None = sync.info.get(KEEP_KEY)
    if kept is not None:
        kept.append(instance)


event.listen(Session, "loaded_as_persistent", keep)
event.listen(Session, "pending_to_persistent", keep)
event.listen(Session, "before_flush", note_flushing)
event.listen(Session, "after_flush", forget_flushed)
event.listen(Session, "after_soft_rollback", forget_all)
event.listen(Session, "do_orm_execute", forget_on_write)


def read_tables(state: ORMExecuteState) -> set[str]:
    statement = state.statement
    if not isinstance(statement, ClauseElement):
        return set()
    found = {element.name for element in visitors.iterate(statement) if isinstance(element, Table)}
    for mapper in state.all_mappers:
        found.update(table.name for table in mapper.tables if isinstance(table, Table))
    return found


def lazy_autoflush(state: ORMExecuteState) -> None:
    if not state.is_select or state.execution_options.get("autoflush") is not None:
        return
    pending = pending_tables(state.session)
    if not pending:
        return
    tables = read_tables(state)
    if tables and pending.isdisjoint(tables):
        state.update_execution_options(autoflush=False)


event.listen(Session, "do_orm_execute", lazy_autoflush)


def memoized[**P, R](*tables: Any) -> Callable[[Callable[Concatenate[AsyncSession, P], Awaitable[R]]], Callable[Concatenate[AsyncSession, P], Awaitable[R]]]:
    names = table_names(tables)

    def wrap(function: Callable[Concatenate[AsyncSession, P], Awaitable[R]]) -> Callable[Concatenate[AsyncSession, P], Awaitable[R]]:
        name = f"{function.__module__}.{function.__qualname__}"

        async def cached(session: AsyncSession, /, *args: P.args, **kwargs: P.kwargs) -> R:
            key = (args, tuple(sorted(kwargs.items())))
            memo = memo_of(session, name, names)
            if memo is not None and key in memo:
                found: R = memo[key]
                return found
            value = await function(session, *args, **kwargs)
            after = memo_of(session, name, names)
            if after is not None:
                after[key] = value
            return value

        return cached

    return wrap
