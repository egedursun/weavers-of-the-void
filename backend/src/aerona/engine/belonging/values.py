from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import FACTION_KIND_TRAITS, having
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow, MovementSupportRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.regime import CoalitionMemberRow
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.life_traits import FactionKindTrait
from aerona.domain.enums.minds import MindOrigin
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.book import realm_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, living_entity, spoken_language

GUILDS = having(FACTION_KIND_TRAITS, FactionKindTrait.GUILDS)
Value = tuple[int | None, str | None]


async def faction_of(session: AsyncSession, mortal_id: int, guild: bool) -> int | None:
    rows = await session.execute(
        select(FactionMembershipRow.faction_entity_id, FactionProfileRow.kind)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id == mortal_id)
        .order_by(FactionMembershipRow.faction_entity_id)
    )
    return next((faction for faction, kind in rows if (kind in GUILDS) == guild), None)


async def tongue_value(session: AsyncSession, holder: EntityRow) -> Value:
    tongue = await spoken_language(session, holder.id)
    if tongue is None and holder.location_id is not None:
        tongue = await spoken_language(session, holder.location_id)
    return (tongue.id, None) if tongue is not None else (None, None)


async def kind_label(session: AsyncSession, people_id: int | None) -> str | None:
    biology = await session.get(PeopleBiologyRow, people_id) if people_id is not None else None
    return biology.body_plan.value if biology is not None else None


async def mortal_kind(session: AsyncSession, mortal: EntityRow, people_id: int | None) -> Value:
    mind = await session.get(MindProfileRow, mortal.id)
    if mind is not None and mind.origin is not MindOrigin.BORN:
        return (None, mind.origin.value)
    return (None, await kind_label(session, people_id))


async def backed_cause(session: AsyncSession, community_id: int) -> int | None:
    found = await session.scalar(
        select(MovementSupportRow.movement_entity_id)
        .where(MovementSupportRow.community_entity_id == community_id)
        .order_by(MovementSupportRow.share.desc(), MovementSupportRow.movement_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def joined_cause(session: AsyncSession, mortal_id: int) -> int | None:
    found = await session.scalar(
        select(FactionMembershipRow.faction_entity_id)
        .join(MovementProfileRow, MovementProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id == mortal_id)
        .order_by(FactionMembershipRow.faction_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


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
        IdentityLayer.LANGUAGE: await tongue_value(session, community),
        IdentityLayer.KIND: (None, await kind_label(session, folk.id if folk is not None else None)),
        IdentityLayer.CAUSE: (await backed_cause(session, community.id), None),
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
    folk = await own_people(session, mortal)
    return {
        IdentityLayer.PEOPLE: (folk, None),
        IdentityLayer.FAITH: (await BondRepository(session).patron(mortal.id), None),
        IdentityLayer.CLASS: (None, mortal.social_class.value if mortal.social_class is not None else None),
        IdentityLayer.LOCALITY: (mortal.location_id, None),
        IdentityLayer.HOUSE: (house, None),
        IdentityLayer.PROFESSION: (await faction_of(session, mortal.id, True), None),
        IdentityLayer.GENERATION: (None, generation),
        IdentityLayer.POLITY: (realm, None),
        IdentityLayer.CIRCLE: (circle or await faction_of(session, mortal.id, False), None),
        IdentityLayer.LANGUAGE: await tongue_value(session, mortal),
        IdentityLayer.KIND: await mortal_kind(session, mortal, folk),
        IdentityLayer.CAUSE: (await joined_cause(session, mortal.id), None),
    }


async def values_of(session: AsyncSession, atlas: RegionAtlas, holder: EntityRow) -> dict[IdentityLayer, Value]:
    if holder.entity_type is EntityType.MORTAL:
        return await mortal_values(session, atlas, holder)
    return await community_values(session, atlas, holder)
