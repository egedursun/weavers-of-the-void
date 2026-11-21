from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import CollaborationFate
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.reckoning import MeasureStage

HARM_MARKS = ("justice.%", "%execut%", "%massacre%", "%purge%", "%tortur%", "%oppress%")
ACTS_NAMED = 5


@dataclass
class ReckoningTally:
    opened: int = 0
    trials: int = 0
    convicted: int = 0
    acquitted: int = 0
    pardoned: int = 0
    barred: int = 0
    inquiries: int = 0
    restitutions: int = 0
    reparations: int = 0
    revolts: int = 0
    fled: int = 0
    closed: int = 0


async def collaborators(session: AsyncSession, row: ReckoningRow) -> list[EntityRow]:
    if row.fallen_node_id is None:
        return []
    regimes = select(OccupationRegimeRow.id).where(
        OccupationRegimeRow.occupier_entity_id == row.fallen_node_id, OccupationRegimeRow.owner_polity_id == row.polity_entity_id
    )
    query = select(CollaborationRow.collaborator_node_id).where(CollaborationRow.regime_id.in_(regimes), CollaborationRow.fate != CollaborationFate.KILLED)
    found: list[EntityRow] = []
    for node in sorted(set(await session.scalars(query))):
        holder = await session.get(EntityRow, node)
        if holder is not None and holder.entity_type is EntityType.MORTAL and holder.status is EntityStatus.CANON:
            found.append(holder)
    return found


async def servants(session: AsyncSession, row: ReckoningRow) -> list[tuple[EntityRow, OfficeRow | None]]:
    found: list[tuple[EntityRow, OfficeRow | None]] = []
    query = select(OfficeRow).where(
        OfficeRow.polity_entity_id == row.polity_entity_id, OfficeRow.holder_entity_id.is_not(None), OfficeRow.kind != OfficeKind.RULER
    )
    for office in await session.scalars(query.order_by(OfficeRow.id)):
        if office.since_epoch > row.fallen_epoch and office.appointed_by_entity_id != row.fallen_node_id:
            continue
        holder = await session.get(EntityRow, office.holder_entity_id)
        if holder is not None and holder.entity_type is EntityType.MORTAL and holder.status is EntityStatus.CANON:
            found.append((holder, office))
    seen = {holder.id for holder, _office in found}
    found.extend((holder, None) for holder in await collaborators(session, row) if holder.id not in seen)
    return found


async def acts_of(session: AsyncSession, accused: int, before: int) -> list[int]:
    query = (
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(
            IncidentParticipantRow.node_id == accused,
            IncidentParticipantRow.role == IncidentRole.ACTOR,
            IncidentRow.epoch <= before,
            or_(*(IncidentRow.kind.like(mark) for mark in HARM_MARKS)),
        )
        .order_by(IncidentRow.id.desc())
        .limit(ACTS_NAMED)
    )
    return sorted(await session.scalars(query))


async def measures_of(session: AsyncSession, reckoning_id: int, stage: MeasureStage | None = None) -> list[ReckoningMeasureRow]:
    query = select(ReckoningMeasureRow).where(ReckoningMeasureRow.reckoning_id == reckoning_id)
    if stage is not None:
        query = query.where(ReckoningMeasureRow.stage == stage)
    return list(await session.scalars(query.order_by(ReckoningMeasureRow.id)))


async def case_of(session: AsyncSession, reckoning_id: int, accused: int) -> ReckoningCaseRow | None:
    query = select(ReckoningCaseRow).where(ReckoningCaseRow.reckoning_id == reckoning_id, ReckoningCaseRow.accused_node_id == accused)
    return await session.scalar(query.limit(1))


async def realm_of(session: AsyncSession, row: ReckoningRow) -> PolityProfileRow | None:
    return await session.get(PolityProfileRow, row.polity_entity_id)
