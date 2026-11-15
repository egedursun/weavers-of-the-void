from collections import Counter
from collections.abc import Awaitable, Callable, Hashable, Iterable
from dataclasses import dataclass, field
from typing import Any, Concatenate

from sqlalchemy import Table, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstanceState, Mapper, ORMExecuteState, Session
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ClauseElement

MEMO_KEY = "aerona.read_memo"
FLUSHING_KEY = "aerona.read_memo.flushing"
PENDING_KEY = "aerona.read_memo.pending"
KEEP_KEY = "aerona.read_memo.keep"
READ_SHAPES_KEPT = 20_000
READ_SHAPES: dict[Hashable, frozenset[str]] = {}
DIRTY_KEY = "aerona.read_memo.dirty"
EVERY_TABLE: frozenset[str] = frozenset()
STRUCTURAL: dict[str, frozenset[str]] = {"entities": frozenset({"entity_type", "status", "location_id", "world_id", "creator_son_id"})}


@dataclass
class Memo:
    tables: frozenset[str]
    live: bool = False
    values: dict[Hashable, Any] = field(default_factory=dict)


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


MAPPER_TABLES: dict[Mapper[Any], frozenset[str]] = {}


def mapper_tables(mapper: Mapper[Any]) -> frozenset[str]:
    found = MAPPER_TABLES.get(mapper)
    if found is None:
        names: set[str] = set()
        for table in mapper.tables:
            if isinstance(table, Table):
                names.add(table.name)
                if table.name in STRUCTURAL:
                    names.add(f"{table.name}.other")
        found = MAPPER_TABLES[mapper] = frozenset(names)
    return found


class DirtyStates(set[InstanceState[Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.mappers: Counter[Mapper[Any]] = Counter()
        self.version = 0

    def count(self, mapper: Mapper[Any], step: int) -> None:
        before = self.mappers[mapper]
        after = before + step
        if after <= 0:
            del self.mappers[mapper]
        else:
            self.mappers[mapper] = after
        if (before > 0) != (after > 0):
            self.version += 1

    def add(self, state: InstanceState[Any]) -> None:
        if state not in self:
            super().add(state)
            self.count(state.mapper, 1)

    def discard(self, state: object) -> None:
        if isinstance(state, InstanceState) and state in self:
            super().discard(state)
            self.count(state.mapper, -1)

    def remove(self, state: InstanceState[Any]) -> None:
        if state not in self:
            raise KeyError(state)
        self.discard(state)

    def pop(self) -> InstanceState[Any]:
        state = super().pop()
        self.count(state.mapper, -1)
        return state

    def clear(self) -> None:
        super().clear()
        self.mappers.clear()
        self.version += 1

    def tables(self) -> set[str]:
        return {name for mapper in self.mappers for name in mapper_tables(mapper)}


def track_dirty(sync: Session) -> None:
    if not isinstance(sync.identity_map._modified, DirtyStates):
        tracked = DirtyStates()
        for state in sync.identity_map._modified:
            tracked.add(state)
        sync.identity_map._modified = tracked


def dirty_tables(sync: Session, modified: set[InstanceState[Any]]) -> set[str]:
    if isinstance(modified, DirtyStates):
        cached: tuple[int, int, set[str]] | None = sync.info.get(DIRTY_KEY)
        if cached is not None and cached[0] == id(modified) and cached[1] == modified.version:
            return cached[2]
        found = modified.tables()
        sync.info[DIRTY_KEY] = (id(modified), modified.version, found)
        return found
    return state_tables(modified)


def touched_rows[T](sync: Session, row_type: type[T]) -> tuple[list[T], list[T], list[T]]:
    new = [row for row in sync._new.values() if isinstance(row, row_type)]
    deleted = [row for row in sync._deleted.values() if isinstance(row, row_type)]
    modified = sync.identity_map._modified
    if isinstance(modified, DirtyStates) and not any(issubclass(mapper.class_, row_type) for mapper in modified.mappers):
        return new, [], deleted
    dirty = [row for state in modified if state not in sync._deleted and isinstance(row := state.obj(), row_type)]
    return new, dirty, deleted


def structural(mapper: Mapper[Any]) -> bool:
    return any(name in STRUCTURAL for name in mapper_tables(mapper))


def modified_tables(sync: Session) -> set[str]:
    modified = sync.identity_map._modified
    if not isinstance(modified, DirtyStates):
        return state_tables(modified, whole=False)
    found = {name for mapper in modified.mappers if not structural(mapper) for name in mapper_tables(mapper)}
    watched = {mapper for mapper in modified.mappers if structural(mapper)}
    if watched:
        found |= state_tables((state for state in modified if state.mapper in watched), whole=False)
    return found


def reshaped_tables(sync: Session) -> set[str]:
    if not sync._new and not sync._deleted:
        return set()
    return {name for state in [*sync._new, *sync._deleted] for name in mapper_tables(state.mapper)}


def pending_tables(sync: Session) -> set[str]:
    modified = sync.identity_map._modified
    if not sync._new and not sync._deleted and not modified:
        return set()
    signature = (len(sync._new), len(sync._deleted), len(modified))
    cached: tuple[tuple[int, int, int], set[str]] | None = sync.info.get(PENDING_KEY)
    if cached is not None and cached[0] == signature:
        return cached[1]
    found = {name for state in [*sync._new, *sync._deleted] for name in mapper_tables(state.mapper)} | dirty_tables(sync, modified)
    sync.info[PENDING_KEY] = (signature, found)
    return found


class MemoTable(dict[str, Memo]):
    def __init__(self) -> None:
        super().__init__()
        self.plain: dict[str, set[str]] = {}
        self.live: dict[str, set[str]] = {}
        self.every: set[str] = set()

    def keep(self, name: str, memo: Memo) -> None:
        self[name] = memo
        if not memo.tables:
            self.every.add(name)
            return
        index = self.live if memo.live else self.plain
        for table in memo.tables:
            index.setdefault(table, set()).add(name)

    def touched(self, changed: set[str], reshaped: set[str] | None) -> set[str]:
        found = set(self.every)
        for table in changed:
            found.update(self.plain.get(table, ()))
        for table in reshaped if reshaped is not None else changed:
            found.update(self.live.get(table, ()))
        return found


def memos(sync: Session) -> MemoTable:
    found = sync.info.get(MEMO_KEY)
    if not isinstance(found, MemoTable):
        found = sync.info[MEMO_KEY] = MemoTable()
    return found


def memo_for(sync: Session, name: str, tables: frozenset[str] = EVERY_TABLE, live: bool = False) -> dict[Hashable, Any] | None:
    pending = reshaped_tables(sync) if live else pending_tables(sync)
    if pending and (not tables or not tables.isdisjoint(pending)):
        return None
    table = memos(sync)
    memo = table.get(name)
    if memo is None:
        memo = Memo(tables, live)
        table.keep(name, memo)
    return memo.values


def memo_of(session: AsyncSession, name: str, tables: frozenset[str] = EVERY_TABLE, live: bool = False) -> dict[Hashable, Any] | None:
    return memo_for(session.sync_session, name, tables, live)


def forget(sync: Session, changed: set[str] | None, reshaped: set[str] | None = None) -> None:
    sync.info.pop(PENDING_KEY, None)
    table = memos(sync)
    if changed is None:
        sync.info[MEMO_KEY] = MemoTable()
        return
    for name in table.touched(changed, reshaped):
        table.pop(name, None)


def flushing_tables(sync: Session) -> set[str]:
    return state_tables([*sync._new, *sync._deleted]) | modified_tables(sync)


def note_flushing(sync: Session, *_: object) -> None:
    sync.info[FLUSHING_KEY] = (flushing_tables(sync), reshaped_tables(sync))


def forget_flushed(sync: Session, *_: object) -> None:
    changed, reshaped = sync.info.pop(FLUSHING_KEY, (set(), set()))
    forget(sync, changed | flushing_tables(sync), reshaped | reshaped_tables(sync))


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
    shape = statement._generate_cache_key()
    known = READ_SHAPES.get(shape.key) if shape is not None else None
    if known is not None:
        return set(known)
    found = {element.name for element in visitors.iterate(statement) if isinstance(element, Table)}
    for mapper in state.all_mappers:
        found.update(table.name for table in mapper.tables if isinstance(table, Table))
    if shape is not None:
        if len(READ_SHAPES) >= READ_SHAPES_KEPT:
            READ_SHAPES.clear()
        READ_SHAPES[shape.key] = frozenset(found)
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
