from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Diet, SpeciesClass
from aerona.domain.enums.entity import EntityType
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, make_entity


async def two_kinds(session: AsyncSession, realm: Realm) -> Ids:
    first = await make_entity(session, "Reed Moth", EntityType.SPECIES, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    second = await make_entity(session, "Marsh Lily", EntityType.SPECIES, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    session.add(SpeciesProfileRow(species_entity_id=first.id, species_class=SpeciesClass.ANIMAL, body_plan=BodyPlan.INSECTOID, diet=Diet.HERBIVORE))
    session.add(SpeciesProfileRow(species_entity_id=second.id, species_class=SpeciesClass.PLANT, body_plan=BodyPlan.ARBOREAL, diet=Diet.PHOTOSYNTHETIC))
    await session.flush()
    return {"first": first.id, "second": second.id}


async def town_dweller(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    await session.flush()
    return {}


def first_kind(_realm: Realm, ids: Ids) -> int:
    return ids["first"]


def second_kind(_realm: Realm, ids: Ids) -> int:
    return ids["second"]
