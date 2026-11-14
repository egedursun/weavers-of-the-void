from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.regime import CoalitionMemberRow
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.book import realm_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, living_entity

GUILDS = frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.SCHOLARS_ACADEMY, FactionKind.PRIESTHOOD, FactionKind.WARRIOR_ORDER})
Value = tuple[int | None, str | None]


async def faction_of(session: AsyncSession, mortal_id: int, guild: bool) -> int | None:
    rows = await session.execute(
        select(FactionMembershipRow.faction_entity_id, FactionProfileRow.kind)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id == mortal_id)
        .order_by(FactionMembershipRow.faction_entity_id)
    )
    return next((faction for faction, kind in rows if (kind in GUILDS) == guild), None)


async def community_values(session: AsyncSession, atlas: RegionAtlas, community: EntityRow) -> dict[IdentityLayer, Value]:
    folk = await people_of(session, community)
    return {
        IdentityLayer.PEOPLE: (folk.id if folk is not None else None, None),
        IdentityLayer.FAITH: (await BondRepository(session).patron(community.id), None),
        IdentityLayer.CLASS: (None, None),
        IdentityLayer.LOCALITY: (atlas.top_region(community.id), None),
        IdentityLayer.HOUSE: (None, None),
        IdentityLayer.PROFESSION: (None, None),
        IdentityLayer.GENERATION: (None, None),
        IdentityLayer.POLITY: (await realm_of(session, community.id), None),
        IdentityLayer.CIRCLE: (None, None),
    }


async def own_people(session: AsyncSession, mortal: EntityRow) -> int | None:
    for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[mortal.id]):
        ancestor = await living_entity(session, bond.target_node_id)
        if ancestor is not None and ancestor.entity_type is EntityType.PEOPLE:
            return ancestor.id
    folk = await people_of(session, mortal)
    return folk.id if folk is not None else None


async def mortal_values(session: AsyncSession, atlas: RegionAtlas, mortal: EntityRow) -> dict[IdentityLayer, Value]:
    house = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal.id).limit(1))
    generation = await session.scalar(
        select(AgeSetRow.name).join(AgeSetMemberRow, AgeSetMemberRow.age_set_id == AgeSetRow.id).where(AgeSetMemberRow.mortal_entity_id == mortal.id).limit(1)
    )
    realm = await realm_of(session, mortal.id) or (await realm_of(session, mortal.location_id) if mortal.location_id is not None else None)
    circle = await session.scalar(select(CoalitionMemberRow.polity_entity_id).where(CoalitionMemberRow.mortal_entity_id == mortal.id).limit(1))
    return {
        IdentityLayer.PEOPLE: (await own_people(session, mortal), None),
        IdentityLayer.FAITH: (await BondRepository(session).patron(mortal.id), None),
        IdentityLayer.CLASS: (None, mortal.social_class.value if mortal.social_class is not None else None),
        IdentityLayer.LOCALITY: (mortal.location_id, None),
        IdentityLayer.HOUSE: (house, None),
        IdentityLayer.PROFESSION: (await faction_of(session, mortal.id, True), None),
        IdentityLayer.GENERATION: (None, generation),
        IdentityLayer.POLITY: (realm, None),
        IdentityLayer.CIRCLE: (circle or await faction_of(session, mortal.id, False), None),
    }


async def values_of(session: AsyncSession, atlas: RegionAtlas, holder: EntityRow) -> dict[IdentityLayer, Value]:
    if holder.entity_type is EntityType.MORTAL:
        return await mortal_values(session, atlas, holder)
    return await community_values(session, atlas, holder)
