from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import PlaceRule

RECORD_TABLES = (
    IncidentRow,
    IncidentParticipantRow,
    IncidentFactRow,
    IncidentStepRow,
    IncidentStepStateRow,
    IncidentTermRow,
    StateChangeRow,
    StateChangeTermRow,
    ChronicleRow,
    ChronicleEntityRow,
)
FULL_SHARE = 100.0
THOUSAND = 1000


@dataclass(frozen=True)
class RecordCounts:
    rows: int
    mortals: int


async def record_counts(session: AsyncSession) -> RecordCounts:
    rows = 0
    for table in RECORD_TABLES:
        rows += int(await session.scalar(select(func.count()).select_from(table)) or 0)
    mortals = await session.scalar(
        select(func.count()).select_from(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    )
    return RecordCounts(rows=rows, mortals=int(mortals or 0))


def rows_per_thousand(before: RecordCounts, after: RecordCounts, epochs: int) -> float:
    mortals = max(1, (before.mortals + after.mortals) // 2)
    return (after.rows - before.rows) / max(1, epochs) / mortals * THOUSAND


async def terms_share(session: AsyncSession, since_change_id: int = 0) -> float:
    numeric = (
        select(StateChangeRow.id, StateChangeRow.incident_id, IncidentRow.kind)
        .outerjoin(IncidentRow, IncidentRow.id == StateChangeRow.incident_id)
        .where(
            StateChangeRow.id > since_change_id,
            StateChangeRow.operation == LedgerOperation.UPDATE,
            StateChangeRow.actor_kind == ActorKind.ENGINE,
            StateChangeRow.after_number.is_not(None),
        )
    )
    explained = set(await session.scalars(select(StateChangeTermRow.change_id).where(StateChangeTermRow.change_id > since_change_id).distinct()))
    reasoned = set(await session.scalars(select(IncidentTermRow.incident_id).distinct()))
    total = 0
    held = 0
    for change_id, incident_id, kind in await session.execute(numeric):
        total += 1
        spec = INCIDENT_KINDS.get(kind) if kind is not None else None
        if change_id in explained or incident_id in reasoned or (spec is not None and spec.direct):
            held += 1
    return FULL_SHARE * held / total if total else FULL_SHARE


async def place_share(session: AsyncSession, since_incident_id: int = 0) -> float:
    required = [key for key, spec in INCIDENT_KINDS.items() if spec.place is PlaceRule.REQUIRED]
    if not required:
        return FULL_SHARE
    chosen = select(IncidentRow.place_entity_id).where(IncidentRow.id > since_incident_id, IncidentRow.kind.in_(required))
    total = 0
    placed = 0
    for place in await session.scalars(chosen):
        total += 1
        placed += 1 if place is not None else 0
    return FULL_SHARE * placed / total if total else FULL_SHARE
