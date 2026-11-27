from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.onlookers import ONLOOKER_ROLES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.moment import Moment, latest

ENDINGS = "record_endings"


async def last_record(session: AsyncSession, node: int, epoch: int) -> Moment | None:
    named = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node, IncidentParticipantRow.role.not_in(sorted(ONLOOKER_ROLES)))
    rows = await session.execute(
        select(IncidentRow.year, IncidentRow.season, IncidentRow.day, IncidentRow.hour).where(
            IncidentRow.id.in_(named), IncidentRow.epoch == epoch, IncidentRow.year.is_not(None)
        )
    )
    return latest(*(Moment(year, season, day, hour) for year, season, day, hour in rows if year is not None))


async def mortal_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    floors: list[Moment | None] = []
    for node in sorted({node for node in nodes if node is not None}):
        entity = await session.get(EntityRow, node)
        if entity is not None and entity.entity_type is EntityType.MORTAL and entity.status is EntityStatus.DEAD:
            year = getattr(entity.stats, "death_year", None)
            if isinstance(year, int):
                floors.append(Moment(year))
    return latest(*floors)


async def ended_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    ends: dict[tuple[int, int], Moment | None] = session.sync_session.info.setdefault(ENDINGS, {})
    floors: list[Moment | None] = []
    for node in sorted({node for node in nodes if node is not None}):
        entity = await session.get(EntityRow, node)
        if entity is None or entity.status in (EntityStatus.CANON, EntityStatus.REJECTED) or entity.entity_type is EntityType.MORTAL:
            continue
        if entity.end_epoch is not None:
            key = (entity.id, entity.end_epoch)
            if key not in ends:
                ends[key] = await last_record(session, entity.id, entity.end_epoch)
            floors.append(ends[key])
    return latest(*floors)


async def death_floor(session: AsyncSession, nodes: Iterable[int]) -> Moment | None:
    return latest(await mortal_floor(session, nodes), await ended_floor(session, nodes))
