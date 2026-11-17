from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.integrity import StructureSectionRow
from aerona.db.tables.mind import FearRow, PressureRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.society_depth import DriftCauseRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import FearKind, PressureKind, ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.enums.structure import SectionRole, StructureKind, StructureSection
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.models.entity_stats import CelestialStats, OuterBeingStats, PeopleStats, StructureStats, VesselStats
from tests.tools.every_setup import led_faction, rival_realm, ruler, second_mortal
from tests.tools.every_setup_crafts import people_home
from tests.tools.factories import Realm, make_entity

Ids = dict[str, int]


async def ruler_at_home(session: AsyncSession, realm: Realm) -> Ids:
    return {**await ruler(session, realm), **await people_home(session, realm)}


async def sky_body(session: AsyncSession, realm: Realm) -> Ids:
    body = await make_entity(session, "The Pale Wanderer", EntityType.CELESTIAL, world_id=realm.cosmos.world_id, stats=CelestialStats())
    return {**await people_home(session, realm), "celestial": body.id}


async def people_before(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    elder = await make_entity(session, "The First Folk", EntityType.PEOPLE, world_id=realm.cosmos.world_id, stats=PeopleStats())
    session.add(HolderTechniqueRow(holder_entity_id=elder.id, technique=next(iter(Technique))))
    await session.flush()
    return {**found, "predecessor": elder.id}


async def subject_of_people(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler_at_home(session, realm)
    other = await second_mortal(session, realm)
    row = await session.get(EntityRow, other["mortal"])
    assert row is not None
    row.location_id = realm.settlement_id
    await session.flush()
    return {**found, "subject": other["mortal"]}


async def faction_leader(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    return {**found, "faction": await led_faction(session, realm, next(iter(FactionKind)), "The Open Hands")}


async def boss_at_home(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    return {**found, "faction": await led_faction(session, realm, FactionKind.CRIME_FAMILY, "The Quiet Ledger")}


async def fearful(session: AsyncSession, realm: Realm) -> Ids:
    row = FearRow(holder_node_id=realm.mortal_id, kind=next(iter(FearKind)), strength=40, since_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    return {"fear": row.id}


async def pressed(session: AsyncSession, realm: Realm) -> Ids:
    session.add(PressureRow(entity_id=realm.mortal_id, pressure=next(iter(PressureKind)), value=40))
    await session.flush()
    return {}


async def drifting_town(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    session.add(DriftCauseRow(community_entity_id=realm.settlement_id, cause=next(iter(DriftCause)), axis=next(iter(ValueAxis)), amount=12, total=12, epoch=0))
    await session.flush()
    return found


async def aboard(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    vessel = await make_entity(
        session, "The Long Reach", EntityType.VESSEL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=VesselStats()
    )
    session.add(VesselProfileRow(entity_id=vessel.id, kind=next(iter(VehicleKind))))
    await session.flush()
    return {**found, "vessel": vessel.id}


async def noble_born(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.social_class = SocialClass.NOBLE
    await session.flush()
    return {}


async def realms_with_hearts(session: AsyncSession, realm: Realm) -> Ids:
    found = await rival_realm(session, realm)
    for polity_id, core_id in ((found["polity"], realm.settlement_id), (found["rival"], realm.people_id)):
        profile = await session.get(PolityProfileRow, polity_id)
        assert profile is not None
        profile.core_entity_id = core_id
    await session.flush()
    return found


async def worn_building(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    building = await make_entity(
        session, "The Old Granary", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=StructureStats()
    )
    session.add(StructureProfileRow(structure_entity_id=building.id, kind=StructureKind.GRANARY))
    section = next(iter(StructureSection))
    session.add(StructureSectionRow(structure_entity_id=building.id, section=section, role=next(iter(SectionRole)), condition=50, locked=[]))
    await session.flush()
    return {**found, "structure": building.id}


async def town_of_maimed(session: AsyncSession, realm: Realm) -> Ids:
    found = await people_home(session, realm)
    session.add(MaimedCohortRow(community_entity_id=realm.settlement_id, kind=next(iter(MaimedKind)), count=3, veterans=1, updated_epoch=0))
    await session.flush()
    return found


async def outer_near(session: AsyncSession, realm: Realm) -> Ids:
    being = await make_entity(
        session, "The Hollow Guest", EntityType.OUTER_BEING, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=OuterBeingStats()
    )
    return {"outer": being.id}
