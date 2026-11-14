from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import InsurerRow
from aerona.db.tables.economy import ResourceProfileRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, MaterialOrigin
from tests.tools.factories import Realm, connect

Ids = dict[str, int]
PROPERTIES = {
    "hardness": 70,
    "toughness": 60,
    "weight": 40,
    "edge": 50,
    "conductivity": 60,
    "sanctity": 40,
    "corruption": 10,
    "rarity": 80,
    "base_value": 70,
    "decay": 5,
}


async def material_resource(session: AsyncSession, realm: Realm) -> Ids:
    material = WorldMaterialRow(
        world_id=realm.cosmos.world_id, origin=MaterialOrigin.GOD_REMAINS, name="Starbone", family=MaterialFamily.EXOTIC, created_epoch=0, **PROPERTIES
    )
    session.add(material)
    await session.flush()
    profile = await session.get(ResourceProfileRow, realm.resource_id)
    if profile is None:
        profile = ResourceProfileRow(
            resource_entity_id=realm.resource_id,
            commodity=CommodityKind.ORE,
            reserve=100,
            initial_reserve=100,
            richness=50,
            extraction_difficulty=30,
            quality=50,
        )
        session.add(profile)
    profile.world_material_id = material.id
    await session.flush()
    return {"material": material.id}


async def town_insurer(session: AsyncSession, realm: Realm) -> Ids:
    faction = await session.get(EntityRow, realm.faction_id)
    me = await session.get(EntityRow, realm.mortal_id)
    assert faction is not None and me is not None
    faction.location_id = realm.settlement_id
    me.location_id = realm.settlement_id
    session.add(InsurerRow(insurer_entity_id=faction.id, pool=30, premium_pct=5, locked=[]))
    profile = await session.get(MortalProfileRow, realm.mortal_id)
    if profile is None:
        session.add(MortalProfileRow(entity_id=realm.mortal_id, wealth=60, locked=[]))
    else:
        profile.wealth = 60
    await session.flush()
    return {"insurer": faction.id}


async def people_home(session: AsyncSession, realm: Realm) -> Ids:
    town = await session.get(EntityRow, realm.settlement_id)
    me = await session.get(EntityRow, realm.mortal_id)
    assert town is not None and me is not None
    town.affiliated_entity_id = realm.people_id
    me.location_id = realm.settlement_id
    await connect(session, town.id, realm.people_id, BondKind.DESCENDS_FROM)
    await session.flush()
    return {"people": realm.people_id}
