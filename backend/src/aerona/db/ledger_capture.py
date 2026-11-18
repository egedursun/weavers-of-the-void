import json
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import JSON, Table, event, select, text, tuple_, update
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, UOWTransaction, configure_mappers, object_mapper
from sqlalchemy.orm.base import NO_VALUE, instance_state
from sqlalchemy.sql.elements import ClauseElement

from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.record_context import COLUMN_STAMPS, ROW_STAMP, SCOPE, TERMS, UNCAPTURED, RecordScope, Stamp, Term, change_terms, current_scope, stamp, stamp_row
from aerona.db.tables.agency import ActionRecordRow, AgentTurnRow, TurnCounterRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind

RowKey = tuple[str, str]
RowValues = dict[str, Any]
LEDGER_TABLES = frozenset({LedgerEntryRow.__tablename__, LedgerChangeRow.__tablename__})
TURN_TABLES = frozenset({ActionRecordRow.__tablename__, AgentTurnRow.__tablename__, TurnCounterRow.__tablename__})


def jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    return value


def key_text(values: RowValues) -> str:
    if len(values) == 1:
        ((name, value),) = values.items()
        if type(value) is int:
            return f'{{"{name}": {value}}}'
    return json.dumps(values, sort_keys=True, default=str)


@dataclass(frozen=True)
class RowChange:
    table_name: str
    row_key: str
    operation: LedgerOperation
    before: RowValues | None
    after: RowValues | None


@dataclass(frozen=True)
class LedgerDraft:
    epoch: int
    actor_kind: ActorKind
    actor_node_id: int | None
    actor_name: str
    tool: str
    action_kind: ActionKind
    input_summary: str | None


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _raw_rows(connection: Connection, table: Table, where: str, params: dict[str, Any]) -> list[RowValues]:
    statement = text(f'SELECT * FROM "{table.name}" WHERE {where}')
    return [dict(row._mapping) for row in connection.execute(statement, params)]


def _pk_clause(table: Table) -> str:
    return " AND ".join(f'"{column.name}" = :{column.name}' for column in table.primary_key.columns)


def _pk_values(table: Table, row: RowValues) -> RowValues:
    return {column.name: row[column.name] for column in table.primary_key.columns}


@dataclass
class RowTracker:
    session: Session
    untracked: frozenset[str] = LEDGER_TABLES
    before: dict[RowKey, RowValues | None] = field(default_factory=dict)
    keys: dict[RowKey, RowValues] = field(default_factory=dict)
    insert_marks: dict[str, int] = field(default_factory=dict)

    def attach(self) -> None:
        event.listen(self.session, "before_flush", self._before_flush)
        event.listen(self.session, "after_flush", self._after_flush)
        event.listen(self.session, "do_orm_execute", self._on_execute)

    def detach(self) -> None:
        event.remove(self.session, "before_flush", self._before_flush)
        event.remove(self.session, "after_flush", self._after_flush)
        event.remove(self.session, "do_orm_execute", self._on_execute)

    def _remember(self, table: Table, pk: RowValues, before: RowValues | None) -> None:
        if table.name in self.untracked:
            return
        key = (table.name, key_text(pk))
        if key not in self.before:
            self.before[key] = before
            self.keys[key] = pk

    def _object_keys(self, instance: object) -> list[tuple[Table, RowValues]]:
        mapper = object_mapper(instance)
        known = instance_state(instance).identity
        identity = known if known is not None else mapper.primary_key_from_instance(instance)
        by_property = {mapper.get_property_by_column(column).key: value for column, value in zip(mapper.primary_key, identity, strict=True)}
        found: list[tuple[Table, RowValues]] = []
        for table in mapper.tables:
            if isinstance(table, Table):
                pk = {column.name: by_property.get(mapper.get_property_by_column(column).key) for column in table.primary_key.columns}
                if all(value is not None for value in pk.values()):
                    found.append((table, pk))
        return found

    def _snapshot_existing(self, instance: object) -> None:
        connection = self.session.connection()
        for table, pk in self._object_keys(instance):
            if table.name in self.untracked or (table.name, key_text(pk)) in self.before:
                continue
            rows = _raw_rows(connection, table, _pk_clause(table), pk)
            self._remember(table, pk, rows[0] if rows else None)

    def _before_flush(self, session: Session, context: UOWTransaction, instances: object) -> None:
        for instance in list(session.dirty):
            if session.is_modified(instance, include_collections=False):
                self._snapshot_existing(instance)
        for instance in list(session.deleted):
            self._snapshot_existing(instance)

    def _after_flush(self, session: Session, context: UOWTransaction) -> None:
        for instance in list(session.new):
            for table, pk in self._object_keys(instance):
                self._remember(table, pk, None)

    def _on_execute(self, state: ORMExecuteState) -> None:
        statement = state.statement
        target = getattr(statement, "table", None)
        if not isinstance(target, Table) or target.name in self.untracked:
            return
        connection = self.session.connection()
        if state.is_insert:
            if target.name not in self.insert_marks:
                mark = connection.execute(text(f'SELECT coalesce(max(rowid), 0) FROM "{target.name}"')).scalar_one()
                self.insert_marks[target.name] = int(mark)
            return
        if not (state.is_update or state.is_delete):
            return
        where = getattr(statement, "whereclause", None)
        query = select(*target.primary_key.columns)
        if where is not None:
            query = query.where(where)
        for keys in connection.execute(query):
            pk = dict(keys._mapping)
            if (target.name, key_text(pk)) in self.before:
                continue
            rows = _raw_rows(connection, target, _pk_clause(target), pk)
            if rows:
                self._remember(target, pk, None if self._inserted_here(connection, target, pk) else rows[0])

    def _inserted_here(self, connection: Connection, table: Table, pk: RowValues) -> bool:
        mark = self.insert_marks.get(table.name)
        if mark is None:
            return False
        rowid = connection.execute(text(f'SELECT rowid FROM "{table.name}" WHERE {_pk_clause(table)}'), pk).scalar_one_or_none()
        return rowid is not None and int(rowid) > mark

    def _collect_inserts(self, connection: Connection) -> None:
        for name, mark in self.insert_marks.items():
            table = _table(name)
            for row in _raw_rows(connection, table, "rowid > :mark", {"mark": mark}):
                self._remember(table, _pk_values(table, row), None)

    def changes(self, connection: Connection) -> list[RowChange]:
        self._collect_inserts(connection)
        found: list[RowChange] = []
        for key, before in self.before.items():
            name, row_key = key
            table = _table(name)
            rows = _raw_rows(connection, table, _pk_clause(table), self.keys[key])
            after = rows[0] if rows else None
            if before == after:
                continue
            operation = LedgerOperation.INSERT if before is None else LedgerOperation.DELETE if after is None else LedgerOperation.UPDATE
            found.append(RowChange(name, row_key, operation, jsonable(before), jsonable(after)))
        return found


def inserted_action_ids(changes: Iterable[RowChange]) -> list[int]:
    return [
        int(change.after["id"])
        for change in changes
        if change.table_name == ActionRecordRow.__tablename__ and change.operation is LedgerOperation.INSERT and change.after is not None
    ]


async def write_entry(session: AsyncSession, draft: LedgerDraft, changes: list[RowChange]) -> LedgerEntryRow:
    entry = LedgerEntryRow(
        epoch=draft.epoch,
        actor_kind=draft.actor_kind,
        actor_node_id=draft.actor_node_id,
        actor_name=draft.actor_name[:NAME_MAX_LENGTH],
        tool=draft.tool,
        action_kind=draft.action_kind,
        input_summary=draft.input_summary[:LEDGER_SUMMARY_MAX_LENGTH] if draft.input_summary else None,
        applied=[],
        conflicts=[],
    )
    session.add(entry)
    await session.flush()
    action_ids = inserted_action_ids(changes)
    if action_ids:
        await session.execute(update(ActionRecordRow).where(ActionRecordRow.id.in_(action_ids)).values(ledger_entry_id=entry.id))
    session.add_all(
        LedgerChangeRow(
            entry_id=entry.id,
            table_name=change.table_name,
            row_key=change.row_key,
            operation=change.operation,
            before=change.before,
            after={**change.after, "ledger_entry_id": entry.id}
            if change.after is not None and change.table_name == ActionRecordRow.__tablename__
            else change.after,
        )
        for change in changes
    )
    await session.flush()
    return entry


class ChangeCapture:
    def __init__(self, session: AsyncSession, untracked: frozenset[str] = LEDGER_TABLES) -> None:
        self._session = session
        self._tracker = RowTracker(session.sync_session, untracked)
        self._attached = False

    def start(self) -> None:
        if not self._attached:
            self._tracker.attach()
            self._attached = True

    def stop(self) -> None:
        if self._attached:
            self._tracker.detach()
            self._attached = False

    async def changes(self) -> list[RowChange]:
        await self._session.flush()
        self.stop()
        return await self._session.run_sync(lambda sync: self._tracker.changes(sync.connection()))

    async def seal(self, draft: LedgerDraft) -> int | None:
        changes = await self.changes()
        if not changes:
            return None
        return (await write_entry(self._session, draft, changes)).id


@asynccontextmanager
async def capture_changes(session: AsyncSession, untracked: frozenset[str] = LEDGER_TABLES) -> AsyncIterator[ChangeCapture]:
    await session.flush()
    capture = ChangeCapture(session, untracked)
    capture.start()
    try:
        yield capture
    finally:
        capture.stop()


RECORD_TABLES = frozenset(
    {
        "incidents",
        "incident_participants",
        "incident_facts",
        "incident_steps",
        "incident_step_states",
        "incident_terms",
        "state_changes",
        "state_change_terms",
        "state_checkpoints",
        "chronicle",
        LedgerEntryRow.__tablename__,
        LedgerChangeRow.__tablename__,
    }
)
UNCAPTURED_TABLES = RECORD_TABLES | BOOKKEEPING_TABLES
FORMER = "aerona.former_values"
KEY_BATCH = 400
REBUILD_KEYS = "aerona.rebuild_keys"
NODE_ROOT = "nodes"
PENDING_CHANGES = "record_pending_changes"
REBUILDS = "record_rebuilds"
NODE_WORLDS = "record_node_worlds"
SURROGATE_KEY = "id"
CHANGE_COLUMNS = (
    "epoch",
    "year",
    "season",
    "day",
    "hour",
    "table_name",
    "row_key",
    "node_id",
    "operation",
    "field",
    "before_number",
    "before_text",
    "before_node_id",
    "after_number",
    "after_text",
    "after_node_id",
    "actor_kind",
    "actor_node_id",
    "phase",
    "incident_id",
    "step_id",
)
INSERT_CHANGES = f"INSERT INTO state_changes ({', '.join(CHANGE_COLUMNS)}) VALUES ({', '.join('?' for _ in CHANGE_COLUMNS)})"
INSERT_NUMBERED_CHANGES = f"INSERT INTO state_changes (id, {', '.join(CHANGE_COLUMNS)}) VALUES (?, {', '.join('?' for _ in CHANGE_COLUMNS)})"
PRESENT_EPOCH = "epoch.present"
INSERT_TERMS = "INSERT INTO state_change_terms (change_id, position, term, source_node_id, source_incident_id, op, amount) VALUES (?, ?, ?, ?, ?, ?, ?)"


class ValueKind(StrEnum):
    NUMBER = "number"
    NODE = "node"
    TEXT = "text"


@dataclass(frozen=True)
class ColumnPlan:
    key: str
    name: str
    kind: ValueKind


@dataclass(frozen=True)
class TablePlan:
    name: str
    columns: tuple[ColumnPlan, ...]
    primary: tuple[ColumnPlan, ...]
    owner: str | None
    surrogate: bool
    content: tuple[str, ...]

    def column(self, name: str) -> ColumnPlan | None:
        return next((column for column in self.columns if column.name == name), None)


PLANS: dict[Table, TablePlan] = {}
MAPPER_PLANS: dict[Any, tuple[TablePlan, ...]] = {}


def node_tables() -> frozenset[str]:
    names = {NODE_ROOT}
    for mapper in Base.registry.mappers:
        if any(getattr(base, "__tablename__", None) == NODE_ROOT for base in mapper.class_.__mro__[1:]):
            names.update(table.name for table in mapper.tables if isinstance(table, Table))
    return frozenset(names)


def value_kind(column: Any, nodes: frozenset[str]) -> ValueKind:
    if any(key.column.table.name in nodes for key in column.foreign_keys):
        return ValueKind.NODE
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return ValueKind.TEXT
    return ValueKind.NUMBER if python_type in (int, float, bool) and not issubclass(python_type, Enum) else ValueKind.TEXT


def table_plan(table: Table, keys: Mapping[str, str] | None = None) -> TablePlan:
    found = PLANS.get(table)
    if found is not None and keys is None:
        return found
    nodes = node_tables()
    named = keys or {}
    columns = tuple(ColumnPlan(named.get(column.name, column.name), column.name, value_kind(column, nodes)) for column in table.columns)
    primary = tuple(plan for plan in columns if table.columns[plan.name].primary_key)
    owner = next((plan.name for plan in primary if table.name in nodes or plan.kind is ValueKind.NODE), None)
    if owner is None:
        owner = next((plan.name for plan in columns if plan.kind is ValueKind.NODE), None)
    surrogate = len(primary) == 1 and primary[0].name == SURROGATE_KEY and table.columns[SURROGATE_KEY].autoincrement in (True, "auto")
    content = tuple(
        column.name
        for column in table.columns
        if not (surrogate and column.name == SURROGATE_KEY) and not (column.server_default is not None and column.default is None)
    )
    plan = TablePlan(table.name, columns, primary, owner, surrogate, content)
    if keys is None:
        PLANS[table] = plan
    return plan


def mapper_plans(mapper: Any) -> tuple[TablePlan, ...]:
    found = MAPPER_PLANS.get(mapper)
    if found is None:
        plans: list[TablePlan] = []
        for table in mapper.tables:
            if not isinstance(table, Table) or table.name in UNCAPTURED_TABLES:
                continue
            keys = {column.name: prop.key for prop in mapper.column_attrs for column in prop.columns if getattr(column, "table", None) is table}
            plans.append(table_plan(table, keys))
        found = MAPPER_PLANS[mapper] = tuple(plans)
    return found


def typed(kind: ValueKind, value: Any) -> tuple[float | None, str | None, int | None]:
    if value is None:
        return None, None, None
    if kind is ValueKind.NODE and isinstance(value, int):
        return None, None, value
    if kind is ValueKind.NUMBER and isinstance(value, (int, float)) and not isinstance(value, Enum):
        return float(value), None, None
    if isinstance(value, Enum):
        return None, str(value.value), None
    if isinstance(value, str):
        return None, value, None
    return None, json.dumps(jsonable(value), sort_keys=True, default=str), None


def whole_row(values: Mapping[str, Any]) -> str:
    return json.dumps({key: jsonable(value) for key, value in values.items() if not isinstance(value, datetime)}, sort_keys=True, default=str)


@dataclass
class PendingChange:
    values: list[Any]
    terms: tuple[Term, ...]
    scope: RecordScope | None
    owner: int | None


INCIDENT_AT = CHANGE_COLUMNS.index("incident_id")
SYSTEM_ACTOR = ActorKind.SYSTEM.value


def change(
    plan: TablePlan,
    key_values: Mapping[str, Any],
    operation: LedgerOperation,
    found: Stamp | None,
    *,
    column: ColumnPlan | None = None,
    before: Any = None,
    after: Any = None,
    owner: int | None = None,
) -> PendingChange:
    scope, terms = found if found is not None else (current_scope(), ())
    moment = scope.moment if scope is not None else None
    kind = column.kind if column is not None else ValueKind.TEXT
    before_number, before_text, before_node = (None, before, None) if column is None else typed(kind, before)
    after_number, after_text, after_node = (None, after, None) if column is None else typed(kind, after)
    values = [
        scope.epoch if scope is not None else 0,
        moment.year if moment is not None else None,
        moment.season if moment is not None else None,
        moment.day if moment is not None else None,
        moment.hour if moment is not None else None,
        plan.name,
        key_text(dict(key_values)),
        owner,
        operation.value,
        column.name if column is not None else None,
        before_number,
        before_text,
        before_node,
        after_number,
        after_text,
        after_node,
        scope.actor_kind.value if scope is not None else SYSTEM_ACTOR,
        scope.actor_node_id if scope is not None else None,
        scope.phase if scope is not None else None,
        scope.incident_id if scope is not None else None,
        scope.step_id if scope is not None else None,
    ]
    return PendingChange(values, terms if column is not None and kind is ValueKind.NUMBER else (), scope, owner)


def owner_of(plan: TablePlan, values: Mapping[str, Any]) -> int | None:
    value = values.get(plan.owner) if plan.owner is not None else None
    return value if isinstance(value, int) else None


def state_values(plan: TablePlan, state: Any) -> dict[str, Any]:
    source = state.dict
    return {column.name: source.get(column.key) for column in plan.columns if column.key in source}


def state_key(plan: TablePlan, state: Any) -> dict[str, Any]:
    identity = state.identity
    if identity is not None and len(identity) == len(state.mapper.primary_key):
        by_column = {column.name: value for column, value in zip(state.mapper.primary_key, identity, strict=True)}
        if all(column.name in by_column for column in plan.primary):
            return {column.name: by_column[column.name] for column in plan.primary}
    return {column.name: state.dict.get(column.key) for column in plan.primary}


def pending(session: Session) -> list[PendingChange]:
    found: list[PendingChange] | None = session.info.get(PENDING_CHANGES)
    if found is None:
        found = session.info[PENDING_CHANGES] = []
    return found


def capture_new(session: Session, state: Any) -> None:
    for plan in mapper_plans(state.mapper):
        values = state_values(plan, state)
        if consume_rebuilt(session, plan, values, state.info.get(ROW_STAMP)):
            continue
        pending(session).append(
            change(plan, state_key(plan, state), LedgerOperation.INSERT, state.info.get(ROW_STAMP), after=whole_row(values), owner=owner_of(plan, values))
        )


MUTABLE_KEYS: dict[str, frozenset[str]] = {}


def mutable_keys(plan: TablePlan) -> frozenset[str]:
    found = MUTABLE_KEYS.get(plan.name)
    if found is None:
        table = _table(plan.name)
        found = MUTABLE_KEYS[plan.name] = frozenset(
            column.key for column in plan.columns if isinstance(getattr(table.c[column.name].type, "impl_instance", table.c[column.name].type), JSON)
        )
    return found


def unloaded_columns(plan: TablePlan, state: Any) -> list[ColumnPlan]:
    committed = state.committed_state
    mutable = mutable_keys(plan)
    wanted = {key for key, value in committed.items() if value is NO_VALUE or key in mutable}
    return [column for column in plan.columns if column.key in wanted] if wanted else []


def load_former(session: Session, _context: UOWTransaction, _instances: object) -> None:
    if session.info.get(UNCAPTURED):
        return
    wanted: dict[str, list[tuple[Any, dict[str, Any], list[ColumnPlan]]]] = {}
    for instance in captured(session.dirty):
        state = instance_state(instance)
        if not state.committed_state or state.identity is None:
            continue
        for plan in mapper_plans(state.mapper):
            unloaded = unloaded_columns(plan, state)
            if unloaded:
                wanted.setdefault(plan.name, []).append((state, state_key(plan, state), unloaded))
    for name, items in wanted.items():
        stored = rows_by_keys(session.connection(), _table(name), [key for _, key, _ in items])
        for state, key, unloaded in items:
            row = stored.get(key_text(key))
            if row is not None:
                state.info.setdefault(FORMER, {}).update({column.key: row[column.name] for column in unloaded})


def capture_dirty(session: Session, state: Any) -> None:
    committed = state.committed_state
    if not committed:
        return
    former: dict[str, Any] = state.info.get(FORMER, {})
    stamps: dict[str, Stamp] = state.info.get(COLUMN_STAMPS, {})
    for plan in mapper_plans(state.mapper):
        owner: int | None = None
        key: dict[str, Any] | None = None
        for column in plan.columns:
            if column.key not in committed:
                continue
            before = committed[column.key]
            after = state.dict.get(column.key)
            if before is NO_VALUE or column.key in former:
                before = former.get(column.key)
            if before == after:
                continue
            if key is None:
                key = state_key(plan, state)
                owner = owner_of(plan, state_values(plan, state))
            pending(session).append(
                change(
                    plan, key, LedgerOperation.UPDATE, stamps.get(column.key, state.info.get(ROW_STAMP)), column=column, before=before, after=after, owner=owner
                )
            )


def capture_deleted(session: Session, state: Any) -> None:
    for plan in mapper_plans(state.mapper):
        values = state_values(plan, state)
        pending(session).append(
            change(plan, state_key(plan, state), LedgerOperation.DELETE, state.info.get(ROW_STAMP), before=whole_row(values), owner=owner_of(plan, values))
        )


def capture_order(instance: Base) -> tuple[str, str]:
    state = instance_state(instance)
    keys = state.identity if state.identity is not None else tuple(state.dict.get(key) for key in primary_keys(state.mapper))
    return (type(instance).__tablename__, repr(tuple(keys)))


PRIMARY_KEYS: dict[Any, tuple[str, ...]] = {}


def primary_keys(mapper: Any) -> tuple[str, ...]:
    found = PRIMARY_KEYS.get(mapper)
    if found is None:
        found = PRIMARY_KEYS[mapper] = tuple(mapper.get_property_by_column(column).key for column in mapper.primary_key)
    return found


def captured(instances: Iterable[object]) -> list[Base]:
    return sorted((instance for instance in instances if isinstance(instance, Base)), key=capture_order)


def record_flush(session: Session, _context: UOWTransaction) -> None:
    if session.info.get(UNCAPTURED):
        return
    flushed: list[Any] = []
    for instance in captured(session.new):
        state = instance_state(instance)
        capture_new(session, state)
        flushed.append(state)
    for instance in captured(session.dirty):
        state = instance_state(instance)
        capture_dirty(session, state)
        flushed.append(state)
    for instance in captured(session.deleted):
        state = instance_state(instance)
        capture_deleted(session, state)
        flushed.append(state)
    write_pending(session, session.connection())
    for state in flushed:
        if state.info:
            state.info.pop(COLUMN_STAMPS, None)
            state.info.pop(ROW_STAMP, None)
            state.info.pop(FORMER, None)


def row_world(session: Session, connection: Connection, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    known: dict[int, int | None] = session.info.setdefault(NODE_WORLDS, {})
    if node_id not in known:
        found = connection.execute(
            text("SELECT coalesce((SELECT world_id FROM entities WHERE id = :node), (SELECT id FROM worlds WHERE id = :node))"), {"node": node_id}
        ).scalar_one_or_none()
        known[node_id] = int(found) if found is not None else None
    return known[node_id]


def phase_incident(session: Session, connection: Connection, scope: RecordScope, world_id: int | None) -> int:
    found = scope.phase_incidents.get(world_id)
    if found is None:
        table = _table("incidents")
        values: dict[str, Any] = {"kind": scope.key, "epoch": max(1, scope.epoch), "world_id": world_id, "magnitude": 0}
        moment = scope.moment
        for name, value in (
            ("year", moment.year if moment else None),
            ("season", moment.season if moment else None),
            ("day", moment.day if moment else None),
            ("hour", moment.hour if moment else None),
        ):
            if name in table.columns:
                values[name] = value
        inserted = connection.execute(table.insert().values(values)).inserted_primary_key
        if inserted is None:
            raise ValueError("The phase incident got no id.")
        found = int(inserted[0])
        scope.phase_incidents[world_id] = found
    return found


def write_pending(session: Session, connection: Connection) -> None:
    rows = session.info.pop(PENDING_CHANGES, None)
    if not rows:
        return
    for row in rows:
        scope = row.scope
        if scope is not None and row.values[INCIDENT_AT] is None:
            if scope.incident_id is not None:
                row.values[INCIDENT_AT] = scope.incident_id
            elif scope.per_phase:
                row.values[INCIDENT_AT] = phase_incident(session, connection, scope, scope.world_id or row_world(session, connection, row.owner))
    if not any(row.terms for row in rows):
        connection.exec_driver_sql(INSERT_CHANGES, [tuple(row.values) for row in rows])
        return
    first = int(connection.exec_driver_sql("SELECT coalesce(max(id), 0) FROM state_changes").scalar_one()) + 1
    connection.exec_driver_sql(INSERT_NUMBERED_CHANGES, [(first + index, *row.values) for index, row in enumerate(rows)])
    connection.exec_driver_sql(
        INSERT_TERMS,
        [
            (first + index, position, term.key, term.source_node_id, term.source_incident_id, term.op.value, term.amount)
            for index, row in enumerate(rows)
            for position, term in enumerate(row.terms)
        ],
    )


def rebuild_key(plan: TablePlan, values: Mapping[str, Any]) -> str:
    if plan.surrogate:
        return key_text({name: jsonable(values.get(name)) for name in plan.content})
    return key_text({column.name: jsonable(values.get(column.name)) for column in plan.primary})


def consume_rebuilt(session: Session, plan: TablePlan, values: Mapping[str, Any], found: Stamp | None) -> bool:
    baseline: dict[str, dict[str, dict[str, Any]]] | None = session.info.get(REBUILDS)
    rows = baseline.get(plan.name) if baseline is not None else None
    if rows is None:
        return False
    key = rebuild_key(plan, values)
    before = rows.pop(key, None)
    if before is None:
        retire_reused(session, plan, rows, values, found)
        return False
    for column in plan.columns:
        if column.name in values and column.name in plan.content and jsonable(before.get(column.name)) != jsonable(values[column.name]):
            pending(session).append(
                change(
                    plan,
                    {name: values.get(name) for name in (item.name for item in plan.primary)},
                    LedgerOperation.UPDATE,
                    found,
                    column=column,
                    before=before.get(column.name),
                    after=values[column.name],
                    owner=owner_of(plan, values),
                )
            )
    return True


def retire_reused(session: Session, plan: TablePlan, rows: dict[str, dict[str, Any]], values: Mapping[str, Any], found: Stamp | None) -> None:
    if not plan.surrogate:
        return
    table = _table(plan.name)
    index: dict[str, dict[str, str]] = session.info.setdefault(REBUILD_KEYS, {})
    keys = index.get(plan.name)
    if keys is None:
        keys = index[plan.name] = {key_text(_pk_values(table, row)): rebuilt for rebuilt, row in rows.items()}
    stored = keys.pop(key_text({column.name: values.get(column.name) for column in table.primary_key.columns}), None)
    former = rows.pop(stored, None) if stored is not None else None
    if former is not None:
        pending(session).append(change(plan, _pk_values(table, former), LedgerOperation.DELETE, found, before=whole_row(former), owner=owner_of(plan, former)))


def finish_rebuilds(session: Session) -> None:
    session.info.pop(REBUILD_KEYS, None)
    baseline: dict[str, dict[str, dict[str, Any]]] | None = session.info.pop(REBUILDS, None)
    if not baseline:
        return
    for name, rows in baseline.items():
        plan = table_plan(_table(name))
        for values in rows.values():
            pending(session).append(
                change(plan, _pk_values(_table(name), values), LedgerOperation.DELETE, None, before=whole_row(values), owner=owner_of(plan, values))
            )
    write_pending(session, session.connection())


def statement_rows(connection: Connection, table: Table, where: Any) -> list[RowValues]:
    query = select(table)
    if where is not None:
        query = query.where(where)
    return [dict(row._mapping) for row in connection.execute(query)]


def bulk_insert(state: ORMExecuteState, connection: Connection, plan: TablePlan, target: Table, found: Stamp | None) -> Any:
    session = state.session
    mark = int(connection.execute(text(f'SELECT coalesce(max(rowid), 0) FROM "{target.name}"')).scalar_one())
    result = state.invoke_statement()
    for row in _raw_rows(connection, target, "rowid > :mark", {"mark": mark}):
        if not consume_rebuilt(session, plan, row, found):
            pending(session).append(change(plan, _pk_values(target, row), LedgerOperation.INSERT, found, after=whole_row(row), owner=owner_of(plan, row)))
    write_pending(session, connection)
    return result


def bulk_wipe(state: ORMExecuteState, connection: Connection, plan: TablePlan, target: Table) -> Any:
    before_rows = statement_rows(connection, target, None)
    result = state.invoke_statement()
    baseline: dict[str, dict[str, dict[str, Any]]] = state.session.info.setdefault(REBUILDS, {})
    kept = baseline.setdefault(target.name, {})
    for row in before_rows:
        kept.setdefault(rebuild_key(plan, row), row)
    state.session.info.get(REBUILD_KEYS, {}).pop(target.name, None)
    return result


def rows_by_keys(connection: Connection, target: Table, keys: list[RowValues]) -> dict[str, RowValues]:
    columns = list(target.primary_key.columns)
    found: dict[str, RowValues] = {}
    for start in range(0, len(keys), KEY_BATCH):
        chunk = keys[start : start + KEY_BATCH]
        if len(columns) == 1:
            where = columns[0].in_([key[columns[0].name] for key in chunk])
        else:
            where = tuple_(*columns).in_([tuple(key[column.name] for column in columns) for key in chunk])
        for row in connection.execute(select(target).where(where)):
            values = dict(row._mapping)
            found[key_text(_pk_values(target, values))] = values
    return found


def touched_rows(state: ORMExecuteState, connection: Connection, plan: TablePlan, target: Table) -> list[RowValues]:
    if not state.is_executemany:
        return statement_rows(connection, target, getattr(state.statement, "whereclause", None))
    params = state.parameters if isinstance(state.parameters, list) else []
    keys = [{column.name: item.get(column.name) for column in target.primary_key.columns} for item in params if isinstance(item, dict)]
    stored = rows_by_keys(connection, target, keys)
    return [stored[key_text(key)] for key in keys if key_text(key) in stored]


def column_changes(
    plan: TablePlan, key: RowValues, before: RowValues, after: RowValues, found: Stamp | None, *, columns: Iterable[ColumnPlan] | None = None
) -> list[PendingChange]:
    return [
        change(
            plan, key, LedgerOperation.UPDATE, found, column=column, before=before.get(column.name), after=after.get(column.name), owner=owner_of(plan, after)
        )
        for column in (plan.columns if columns is None else columns)
        if jsonable(before.get(column.name)) != jsonable(after.get(column.name))
    ]


def given_values(state: ORMExecuteState, plan: TablePlan, target: Table) -> dict[str, dict[str, Any]] | None:
    params = state.parameters if isinstance(state.parameters, list) else None
    if not state.is_executemany or params is None or not all(isinstance(item, dict) for item in params):
        return None
    names = {column.key: column.name for column in plan.columns}
    primary = {column.name for column in target.primary_key.columns}
    found: dict[str, dict[str, Any]] = {}
    for item in params:
        values = {names[name]: value for name, value in item.items() if name in names}
        if not primary <= set(values) or any(isinstance(value, ClauseElement) for value in values.values()):
            return None
        found[key_text({name: values[name] for name in sorted(primary)})] = values
    return found


def bulk_change(state: ORMExecuteState, connection: Connection, plan: TablePlan, target: Table, found: Stamp | None) -> Any:
    session = state.session
    before_rows = touched_rows(state, connection, plan, target)
    result = state.invoke_statement()
    given = None if state.is_delete else given_values(state, plan, target)
    after_rows = {} if state.is_delete or given is not None else rows_by_keys(connection, target, [_pk_values(target, before) for before in before_rows])
    for before in before_rows:
        key = _pk_values(target, before)
        if state.is_delete:
            pending(session).append(change(plan, key, LedgerOperation.DELETE, found, before=whole_row(before), owner=owner_of(plan, before)))
            continue
        if given is not None:
            values = given.get(key_text(key), {})
            columns = [column for column in plan.columns if column.name in values]
            pending(session).extend(column_changes(plan, key, before, {**before, **values}, found, columns=columns))
            continue
        after = after_rows.get(key_text(key))
        if after is not None:
            pending(session).extend(column_changes(plan, key, before, after, found))
    write_pending(session, connection)
    return result


def capture_bulk(state: ORMExecuteState) -> Any:
    if not (state.is_insert or state.is_update or state.is_delete) or state.session.info.get(UNCAPTURED):
        return None
    target = getattr(state.statement, "table", None)
    if not isinstance(target, Table) or target.name in UNCAPTURED_TABLES:
        return None
    connection = state.session.connection()
    plan = table_plan(target)
    if state.is_insert:
        return bulk_insert(state, connection, plan, target, stamp())
    if state.is_delete and not state.is_executemany and getattr(state.statement, "whereclause", None) is None:
        return bulk_wipe(state, connection, plan, target)
    return bulk_change(state, connection, plan, target, stamp())


def remember_insert(session: Session, instance: object) -> None:
    stamp_row(instance)


def remember_set(target: Any, value: Any, oldvalue: Any, initiator: Any) -> None:
    scope = SCOPE.get()
    collector = TERMS.get()
    if scope is None and collector is None:
        return
    info = target.info
    stamps = info.get(COLUMN_STAMPS)
    if stamps is None:
        stamps = info[COLUMN_STAMPS] = {}
    terms = change_terms(collector)
    if not terms and scope is not None and (initiator.key == "epoch" or initiator.key.endswith("_epoch")) and value == scope.epoch:
        terms = (Term(PRESENT_EPOCH, float(value)),)
    stamps[initiator.key] = (scope, terms)


def finish_on_commit(session: Session) -> None:
    if session.info.get(REBUILDS):
        finish_rebuilds(session)


def install_change_capture() -> None:
    if event.contains(Session, "after_flush", record_flush):
        return
    configure_mappers()
    for mapper in Base.registry.mappers:
        if all(table.name in UNCAPTURED_TABLES for table in mapper.tables):
            continue
        for prop in mapper.column_attrs:
            attribute = getattr(mapper.class_, prop.key, None)
            if attribute is not None and not event.contains(attribute, "set", remember_set):
                event.listen(attribute, "set", remember_set, raw=True)
    event.listen(Session, "before_flush", load_former)
    event.listen(Session, "after_flush", record_flush)
    event.listen(Session, "transient_to_pending", remember_insert)
    event.listen(Session, "do_orm_execute", capture_bulk)
    event.listen(Session, "before_commit", finish_on_commit)
