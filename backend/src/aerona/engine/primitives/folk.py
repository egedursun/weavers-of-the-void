from collections.abc import Iterable

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.queries import active_bonds

HOMELAND_BONDS = (BondKind.RULES, BondKind.LIVES_IN)


async def homes_of(session: AsyncSession, community: EntityRow) -> set[int]:
    places = {community.id}
    if community.entity_type is EntityType.PEOPLE:
        held = await active_bonds(session, HOMELAND_BONDS, sources=[community.id])
        descended = await active_bonds(session, [BondKind.DESCENDS_FROM], targets=[community.id])
        places |= {bond.target_node_id for bond in held if bond.role is BondRole.HOMELAND}
        places |= {bond.source_node_id for bond in descended}
    if community.entity_type is EntityType.POLITY:
        for member_id in await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == community.id)):
            member = await session.get(EntityRow, member_id)
            if member is not None and member.id != community.id:
                places |= await homes_of(session, member)
    return places


async def homes_for(session: AsyncSession, ids: Iterable[int | None]) -> set[int]:
    places: set[int] = set()
    for place_id in ids:
        if place_id is None:
            continue
        found = await session.get(EntityRow, place_id)
        places |= await homes_of(session, found) if found is not None else {place_id}
    return places


async def present_among(session: AsyncSession, ids: Iterable[int | None]) -> ColumnElement[bool]:
    return EntityRow.location_id.in_(sorted(await homes_for(session, ids)))


async def folk_among(session: AsyncSession, ids: Iterable[int | None]) -> ColumnElement[bool]:
    places = sorted(await homes_for(session, ids))
    return or_(EntityRow.location_id.in_(places), EntityRow.affiliated_entity_id.in_(places))


async def present_in(session: AsyncSession, place: EntityRow) -> ColumnElement[bool]:
    return await present_among(session, [place.id])


async def folk_of(session: AsyncSession, community: EntityRow) -> ColumnElement[bool]:
    return await folk_among(session, [community.id])


async def towns_of_people(session: AsyncSession, people_id: int | None) -> list[int]:
    people = await session.get(EntityRow, people_id) if people_id is not None else None
    if people is None:
        return []
    places = sorted(await homes_of(session, people))
    found = await session.scalars(
        select(EntityRow.id)
        .where(EntityRow.id.in_(places), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(found)
