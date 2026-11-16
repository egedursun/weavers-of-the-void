from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import stat_or

LIVE_OUTBREAKS = (OutbreakStatus.ACTIVE, OutbreakStatus.WANING)


async def enclosing(session: AsyncSession, entity: EntityRow | None, kind: EntityType) -> EntityRow | None:
    current = entity
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        if current.entity_type is kind:
            return current
        seen.add(current.id)
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    return None


async def region_of(session: AsyncSession, entity: EntityRow | None) -> EntityRow | None:
    return await enclosing(session, entity, EntityType.REGION)


async def town_of(session: AsyncSession, entity: EntityRow | None) -> EntityRow | None:
    town = await enclosing(session, entity, EntityType.SETTLEMENT)
    if town is not None or entity is None:
        return town
    region = await region_of(session, entity)
    if region is None:
        return None
    towns = await session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == region.id)
        .order_by(EntityRow.id)
    )
    return max(list(towns), key=lambda row: (stat_or(row, "population", 0), -row.id), default=None)


async def church_in(session: AsyncSession, town: EntityRow) -> EntityRow | None:
    rows = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town.id)
    )
    return max(list(rows), key=lambda row: (stat_or(row, "zeal", 0), -row.id), default=None)


async def church_of(session: AsyncSession, town: EntityRow) -> EntityRow | None:
    held_here = select(CultHoldingRow.cult_entity_id).where(CultHoldingRow.holding_entity_id == town.id)
    rows = await session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.CULT,
            EntityRow.status == EntityStatus.CANON,
            or_(EntityRow.location_id == town.id, EntityRow.id.in_(held_here)),
        )
    )
    return max(list(rows), key=lambda row: (stat_or(row, "zeal", 0), -row.id), default=None)


async def plagued_regions(session: AsyncSession) -> set[int]:
    rows = await session.scalars(select(OutbreakRow.region_entity_id).where(OutbreakRow.status.in_(LIVE_OUTBREAKS)))
    return {item for item in rows if item is not None}


async def realm_of_town(session: AsyncSession, town_id: int) -> int | None:
    found = await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    return int(found) if found is not None else None


async def at_war(session: AsyncSession, realm_id: int) -> bool:
    found = await session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id == realm_id, WarSideRow.left_epoch.is_(None), WarRow.status != WarStatus.ENDED)
        .limit(1)
    )
    return found is not None


async def ruler_of(session: AsyncSession, realm_id: int | None) -> int | None:
    if realm_id is None:
        return None
    found = await session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.RULER).order_by(OfficeRow.id).limit(1)
    )
    return int(found) if found is not None else None


async def realm_for(session: AsyncSession, community: EntityRow) -> int | None:
    if community.entity_type is EntityType.POLITY:
        return community.id
    town = await town_of(session, community)
    return await realm_of_town(session, town.id) if town is not None else None


async def realm_ruled_by(session: AsyncSession, mortal_id: int) -> int | None:
    found = await session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == mortal_id, OfficeRow.kind == OfficeKind.RULER).order_by(OfficeRow.id).limit(1)
    )
    return int(found) if found is not None else None


async def patron_of(ctx: TickContext, entity_id: int) -> int | None:
    book = await ctx.divine()
    gods, _ = await book.faithful_of(ctx.session, entity_id)
    return min(gods) if gods else None
