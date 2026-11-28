from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.db.read_memo import KEEP_KEY, pending_tables, register_index, touched_rows

INDEX_PREFIX = "aerona.key_index."


@dataclass
class KeyIndex:
    columns: tuple[str, ...]
    scope: Hashable = None
    rows: dict[tuple[Hashable, ...], list[Any]] = field(default_factory=dict)
    keys: dict[int, tuple[Hashable, ...]] = field(default_factory=dict)

    def key_of(self, row: Any) -> tuple[Hashable, ...]:
        return tuple(getattr(row, column) for column in self.columns)

    def add(self, row: Any) -> None:
        if id(row) in self.keys:
            self.moved(row)
            return
        key = self.key_of(row)
        self.rows.setdefault(key, []).append(row)
        self.keys[id(row)] = key

    def remove(self, row: Any) -> None:
        key = self.keys.pop(id(row), self.key_of(row))
        self.rows[key] = [item for item in self.rows.get(key, []) if item is not row]

    def moved(self, row: Any) -> None:
        if self.keys.get(id(row)) != self.key_of(row):
            self.remove(row)
            self.add(row)


@dataclass(frozen=True)
class IndexSpec:
    row_type: type[Any]
    columns: tuple[str, ...]
    scope_column: str | None = None

    @property
    def key(self) -> str:
        return f"{INDEX_PREFIX}{self.row_type.__tablename__}:{','.join(self.columns)}:{self.scope_column or ''}"

    def covers(self, row: Any, found: KeyIndex) -> bool:
        return isinstance(row, self.row_type) and (self.scope_column is None or getattr(row, self.scope_column) == found.scope)

    @property
    def table(self) -> str:
        return str(self.row_type.__tablename__)


SPECS: dict[str, IndexSpec] = {}


def index_spec(row_type: type[Any], *columns: str, scope: str | None = None) -> IndexSpec:
    spec = IndexSpec(row_type, columns, scope)
    if spec.key not in SPECS:
        SPECS[spec.key] = spec
        register_index(spec.key)
    return spec


async def keyed_rows(session: AsyncSession, spec: IndexSpec, scope: Hashable = None) -> KeyIndex | None:
    sync = session.sync_session
    if KEEP_KEY not in sync.info:
        return None
    kept: dict[Hashable, KeyIndex] | None = sync.info.get(spec.key)
    found = kept.get(scope) if kept is not None else None
    if found is not None:
        follow(sync, spec, found)
        return found
    if spec.table in pending_tables(sync):
        await session.flush()
    kept = sync.info.setdefault(spec.key, {})
    found = kept.get(scope)
    if found is None:
        found = KeyIndex(spec.columns, scope)
        statement = select(spec.row_type)
        if spec.scope_column is not None:
            statement = statement.where(getattr(spec.row_type, spec.scope_column) == scope)
        for row in await session.scalars(statement.order_by(*inspect(spec.row_type).primary_key)):
            found.add(row)
        kept[scope] = found
    return found


def follow(sync: Session, spec: IndexSpec, found: KeyIndex) -> None:
    new, dirty, deleted = touched_rows(sync, spec.row_type)
    for row in new:
        if spec.covers(row, found):
            found.add(row)
    for row in dirty:
        if spec.covers(row, found):
            found.moved(row)
        elif id(row) in found.keys:
            found.remove(row)
    for row in deleted:
        found.remove(row)


def follow_flush(sync: Session, *_: object) -> None:
    for key, spec in SPECS.items():
        kept: dict[Hashable, KeyIndex] | None = sync.info.get(key)
        for found in (kept or {}).values():
            follow(sync, spec, found)


def drop_all(sync: Session, *_: object) -> None:
    for key in SPECS:
        sync.info.pop(key, None)


def drop_on_write(state: ORMExecuteState) -> None:
    if state.is_select:
        return
    target = getattr(state.statement, "table", None)
    name = getattr(target, "name", None)
    for key, spec in SPECS.items():
        if name is None or name == spec.table:
            state.session.info.pop(key, None)


event.listen(Session, "after_flush", follow_flush)
event.listen(Session, "after_soft_rollback", drop_all)
event.listen(Session, "do_orm_execute", drop_on_write)
