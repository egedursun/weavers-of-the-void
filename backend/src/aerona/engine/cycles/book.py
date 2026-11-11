from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import AsabiyyaRow, PolityStressRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import WarStatus
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int


def put(row: object, field: str, value: float, *, low: int = 0, high: int = PERCENT) -> int:
    locked = getattr(row, "locked", None) or []
    if field in locked:
        return int(getattr(row, field))
    found = clamp_int(value, low, high)
    setattr(row, field, found)
    return found


async def realm_towns(session: AsyncSession, polity_id: int) -> list[EntityRow]:
    rows = await session.scalars(
        select(EntityRow)
        .join(PolityMemberRow, PolityMemberRow.member_entity_id == EntityRow.id)
        .where(PolityMemberRow.polity_entity_id == polity_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(rows)


async def polities(session: AsyncSession) -> list[tuple[EntityRow, PolityProfileRow]]:
    rows = await session.execute(
        select(EntityRow, PolityProfileRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows.all()]


async def realm_of(session: AsyncSession, entity_id: int) -> int | None:
    if await session.get(PolityProfileRow, entity_id) is not None:
        return entity_id
    return await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == entity_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )


async def psi_of(session: AsyncSession, entity_id: int | None) -> int:
    if entity_id is None:
        return 0
    polity = await realm_of(session, entity_id)
    row = await session.get(PolityStressRow, polity) if polity is not None else None
    return row.psi if row is not None else 0


async def strain_of(session: AsyncSession, entity_id: int | None) -> int:
    if entity_id is None:
        return 0
    polity = await realm_of(session, entity_id)
    row = await session.get(PolityStressRow, polity) if polity is not None else None
    return round(row.immiseration * row.pressure / PERCENT) if row is not None else 0


async def stress_factor(session: AsyncSession, entity_id: int | None, lift_pct: int) -> float:
    return 1 + await psi_of(session, entity_id) * lift_pct / PERCENT / PERCENT


async def asabiyya_of(session: AsyncSession, entity_ids: Iterable[int | None]) -> int | None:
    found = [row.value for entity_id in entity_ids if entity_id is not None and (row := await session.get(AsabiyyaRow, entity_id)) is not None]
    return max(found) if found else None


async def asabiyya_factor(session: AsyncSession, entity_ids: Iterable[int | None], weight_pct: int) -> float:
    value = await asabiyya_of(session, entity_ids)
    if value is None:
        return 1.0
    return 1 + (value - PERCENT / 2) * weight_pct / PERCENT / (PERCENT / 2)


async def solidarity(session: AsyncSession, community: EntityRow, weight_pct: int) -> float:
    people = community if community.entity_type is EntityType.PEOPLE else await people_of(session, community)
    return await asabiyya_factor(session, [community.id, people.id if people is not None else None, await realm_of(session, community.id)], weight_pct)


async def at_war(ctx: TickContext, entity_ids: set[int]) -> bool:
    if not entity_ids:
        return False
    found = await ctx.session.scalar(
        select(WarSideRow.entity_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(entity_ids), WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        .limit(1)
    )
    return found is not None
