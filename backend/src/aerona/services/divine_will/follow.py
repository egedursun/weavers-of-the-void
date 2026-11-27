import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from functools import cache
from itertools import batched
from typing import Any

from sqlalchemy import ColumnClause, Integer, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.record_edits import INCIDENT, LINE, STEP, Edit
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.ledger import LedgerChangeRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import ChunkSource
from aerona.domain.enums.meta import LedgerOperation
from aerona.services.books.typed import NAMED_TABLES, REFERENCE_LISTS
from aerona.services.divine_will.passages import (
    KEY_SEPARATOR,
    UNREAD_TABLES,
    PassageKey,
    indexed_set,
    line_ref,
    mappers,
    node_ref,
    row_ref,
    season_ref,
    typed_id,
    world_ref,
)

STATE_CURSOR = "state_changes"
LEDGER_CURSOR = "ledger_changes"
NAME_FIELD = "name"
WORLD_FIELD = "world_id"
LOOKUP_BATCH = 500
NODE_TABLE = "nodes"
NODE_SOURCES = (ChunkSource.ENTITY, ChunkSource.SON, ChunkSource.FOREIGN_GOD, ChunkSource.WORLD, ChunkSource.STAR, ChunkSource.CREATOR)
ROWID: ColumnClause[int] = literal_column("rowid", Integer())
OWN_SOURCES: dict[str, ChunkSource] = {
    "sons": ChunkSource.SON,
    "foreign_gods": ChunkSource.FOREIGN_GOD,
    "worlds": ChunkSource.WORLD,
    "stars": ChunkSource.STAR,
    "creator": ChunkSource.CREATOR,
    "lexemes": ChunkSource.WORD,
    "messages": ChunkSource.MESSAGE,
    "councils": ChunkSource.COUNCIL,
    "divine_will_artifacts": ChunkSource.ARTIFACT,
}
RECORD_CURSORS: tuple[tuple[str, Any, Any], ...] = (
    ("incidents", IncidentRow, IncidentRow.id),
    ("incident_participants", IncidentParticipantRow, IncidentParticipantRow.incident_id),
    ("incident_facts", IncidentFactRow, IncidentFactRow.incident_id),
    ("incident_steps", IncidentStepRow, IncidentStepRow.incident_id),
    ("incident_terms", IncidentTermRow, IncidentTermRow.incident_id),
    ("incident_step_states", IncidentStepStateRow, IncidentStepStateRow.step_id),
    ("chronicle", ChronicleRow, ChronicleRow.id),
    ("chronicle_entities", ChronicleEntityRow, ChronicleEntityRow.chronicle_id),
)
LINE_TABLES = frozenset({"chronicle", "chronicle_entities"})
INCIDENT_TABLES = frozenset(name for name, _row, _column in RECORD_CURSORS if name not in LINE_TABLES)


@dataclass
class Affected:
    keys: set[PassageKey] = field(default_factory=set)
    refs: set[str] = field(default_factory=set)
    cursors: dict[str, int] = field(default_factory=dict)
    read: int = 0
    more: bool = False
    incidents: set[int] = field(default_factory=set)
    rumours: set[int] = field(default_factory=set)
    distortions: set[int] = field(default_factory=set)
    steps: set[int] = field(default_factory=set)

    def incident(self, incident_id: Any) -> None:
        if isinstance(incident_id, int) and not isinstance(incident_id, bool):
            self.incidents.add(incident_id)


@cache
def referenced_tables() -> frozenset[str]:
    targets = {foreign.column.table.name for mapper in mappers().values() for column in mapper.local_table.columns for foreign in column.foreign_keys}
    targets |= set(REFERENCE_LISTS.values())
    return frozenset(targets - NAMED_TABLES)


def parsed_key(row_key: str) -> dict[str, Any]:
    try:
        values = json.loads(row_key)
    except ValueError:
        return {}
    return values if isinstance(values, dict) else {}


def single_id(values: Mapping[str, Any]) -> int | None:
    found = values.get("id")
    return found if len(values) == 1 and isinstance(found, int) and not isinstance(found, bool) else None


async def heads(session: AsyncSession) -> dict[str, int]:
    found = {
        STATE_CURSOR: int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0),
        LEDGER_CURSOR: int(await session.scalar(select(func.coalesce(func.max(LedgerChangeRow.id), 0))) or 0),
    }
    for name, row, _column in RECORD_CURSORS:
        found[name] = int(await session.scalar(select(func.coalesce(func.max(ROWID), 0)).select_from(row)) or 0)
    return found


def entity_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if own is None:
        return
    affected.keys.update({(ChunkSource.ENTITY, str(own)), (ChunkSource.NOTE, f"entity{KEY_SEPARATOR}{own}")})
    if changed == WORLD_FIELD:
        affected.refs.add(world_ref(own))


def epoch_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if isinstance(values.get("epoch"), int):
        affected.keys.add((ChunkSource.EPOCH, str(values["epoch"])))


def narrative_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if isinstance(values.get("epoch"), int) and isinstance(values.get("world_id"), int):
        affected.keys.add((ChunkSource.EPOCH, f"{values['epoch']}{KEY_SEPARATOR}{values['world_id']}"))


def map_note_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if own is not None:
        affected.keys.add((ChunkSource.NOTE, f"map{KEY_SEPARATOR}{own}"))


def artifact_part_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if isinstance(values.get("artifact_id"), int):
        affected.keys.add((ChunkSource.ARTIFACT, str(values["artifact_id"])))


def incident_name_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    affected.incident(values.get("incident_id"))


def rumour_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if own is not None:
        affected.rumours.add(own)


def distortion_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if own is not None:
        affected.distortions.add(own)


def season_change(affected: Affected, values: Mapping[str, Any], own: int | None, changed: str | None) -> None:
    if isinstance(values.get("world_id"), int):
        affected.refs.add(season_ref(values["world_id"]))


OWN_CHANGES: dict[str, Callable[[Affected, Mapping[str, Any], int | None, str | None], None]] = {
    "entities": entity_change,
    "epochs": epoch_change,
    "epoch_world_narratives": narrative_change,
    "map_notes": map_note_change,
    "divine_will_artifact_versions": artifact_part_change,
    "divine_will_artifact_nodes": artifact_part_change,
    "incident_names": incident_name_change,
    "rumours": rumour_change,
    "rumour_distortions": distortion_change,
    "world_seasons": season_change,
    "season_onsets": season_change,
}


async def world_head(session: AsyncSession) -> int:
    statement = select(func.coalesce(func.max(StateChangeRow.id), 0)).where(StateChangeRow.table_name.not_in(sorted(UNREAD_TABLES)))
    return int(await session.scalar(statement) or 0)


def take_change(affected: Affected, table: str, row_key: str, operation: LedgerOperation, changed: str | None) -> None:
    values = parsed_key(row_key)
    own = single_id(values)
    if table in indexed_set():
        affected.keys.add((ChunkSource.TYPED_SECTION, typed_id(table, row_key)))
        if own is not None and operation is not LedgerOperation.INSERT and table in referenced_tables():
            affected.refs.add(row_ref(table, own))
    if table in NAMED_TABLES and own is not None and (changed == NAME_FIELD or operation is LedgerOperation.DELETE):
        affected.refs.add(node_ref(own))
    if table == NODE_TABLE and own is not None:
        affected.keys.update((source, str(own)) for source in NODE_SOURCES)
        affected.keys.add((ChunkSource.NOTE, f"entity{KEY_SEPARATOR}{own}"))
    handler = OWN_CHANGES.get(table)
    if handler is not None:
        handler(affected, values, own, changed)
    elif table in OWN_SOURCES and own is not None:
        affected.keys.add((OWN_SOURCES[table], str(own)))


def take_ledger(affected: Affected, table: str, row_key: str, before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> None:
    values = parsed_key(row_key)
    if table == "chronicle":
        own = single_id(values)
        if own is not None:
            affected.keys.add((ChunkSource.CHRONICLE, str(own)))
            affected.refs.add(line_ref(own))
        return
    shown = {**(before or {}), **(after or {}), **values}
    if table == "incidents":
        affected.incident(single_id(values))
    elif table == "incident_step_states":
        step = shown.get("step_id")
        if isinstance(step, int):
            affected.steps.add(step)
    elif table in INCIDENT_TABLES:
        affected.incident(shown.get("incident_id"))


async def resolve(session: AsyncSession, affected: Affected) -> None:
    distortions = sorted(affected.distortions)
    for part in batched(distortions, LOOKUP_BATCH, strict=False):
        affected.rumours.update(await session.scalars(select(RumourDistortionRow.rumour_id).where(RumourDistortionRow.id.in_(part))))
    for part in batched(sorted(affected.rumours), LOOKUP_BATCH, strict=False):
        affected.incidents.update(await session.scalars(select(RumourRow.incident_id).where(RumourRow.id.in_(part))))
    for part in batched(sorted(affected.steps), LOOKUP_BATCH, strict=False):
        affected.incidents.update(await session.scalars(select(IncidentStepRow.incident_id).where(IncidentStepRow.id.in_(part))))
    affected.keys.update((ChunkSource.INCIDENT, str(incident_id)) for incident_id in affected.incidents)


def removed_refs(keys: Iterable[PassageKey]) -> set[str]:
    found: set[str] = set()
    for source, source_id in keys:
        if source is ChunkSource.TYPED_SECTION:
            table, _, row_key = source_id.partition(KEY_SEPARATOR)
            own = single_id(parsed_key(row_key))
            if own is not None and table in referenced_tables():
                found.add(row_ref(table, own))
        elif source in NODE_SOURCES and source_id.isdigit():
            found.add(node_ref(int(source_id)))
    return found


def take_edits(affected: Affected, edits: Iterable[Edit]) -> None:
    for kind, value in edits:
        if kind == INCIDENT:
            affected.incident(value)
        elif kind == STEP:
            affected.steps.add(value)
        elif kind == LINE:
            affected.keys.add((ChunkSource.CHRONICLE, str(value)))
            affected.refs.add(line_ref(value))


async def affected_since(session: AsyncSession, cursors: Mapping[str, int], limit: int, edits: Iterable[Edit] = ()) -> Affected:
    affected = Affected(cursors=dict(cursors))
    take_edits(affected, edits)
    start = cursors.get(STATE_CURSOR, 0)
    rows = (
        await session.execute(
            select(StateChangeRow.id, StateChangeRow.table_name, StateChangeRow.row_key, StateChangeRow.operation, StateChangeRow.field)
            .where(StateChangeRow.id > start)
            .order_by(StateChangeRow.id)
            .limit(limit)
        )
    ).all()
    for change_id, table, row_key, operation, changed in rows:
        take_change(affected, table, row_key, operation, changed)
        affected.cursors[STATE_CURSOR] = int(change_id)
    affected.read += len(rows)
    affected.more |= len(rows) >= limit
    start = cursors.get(LEDGER_CURSOR, 0)
    ledger_rows = (
        await session.execute(
            select(LedgerChangeRow.id, LedgerChangeRow.table_name, LedgerChangeRow.row_key, LedgerChangeRow.before, LedgerChangeRow.after)
            .where(LedgerChangeRow.id > start)
            .order_by(LedgerChangeRow.id)
            .limit(limit)
        )
    ).all()
    for change_id, table, row_key, before, after in ledger_rows:
        take_ledger(affected, table, row_key, before, after)
        affected.cursors[LEDGER_CURSOR] = int(change_id)
    affected.read += len(ledger_rows)
    affected.more |= len(ledger_rows) >= limit
    for name, row, column in RECORD_CURSORS:
        start = cursors.get(name, 0)
        found = (await session.execute(select(ROWID, column).select_from(row).where(start < ROWID).order_by(ROWID).limit(limit))).all()
        for rowid, value in found:
            if name in LINE_TABLES:
                affected.keys.add((ChunkSource.CHRONICLE, str(value)))
            elif name == "incident_step_states":
                affected.steps.add(int(value))
            else:
                affected.incident(value)
            affected.cursors[name] = int(rowid)
        affected.read += len(found)
        affected.more |= len(found) >= limit
    await resolve(session, affected)
    return affected


async def latest_lines(session: AsyncSession, epochs: int) -> tuple[list[int], set[int]]:
    latest = await session.scalar(select(func.max(ChronicleRow.epoch)))
    if latest is None:
        return [], set()
    recent = (ChronicleRow.epoch > latest - epochs) & (ChronicleRow.kind != ChronicleKind.SYSTEM)
    every = list(await session.scalars(select(ChronicleRow.id).where(recent).order_by(ChronicleRow.id)))
    shown = set(await session.scalars(select(ChronicleRow.id).where(recent, shown_lines()).order_by(ChronicleRow.id)))
    return every, shown


def flipped(every: Iterable[int], shown: set[int], held: set[int]) -> set[int]:
    return {line for line in every if (line in shown) != (line in held)}
