from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import MagicSchool, MagicSource
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import ArmyStats, MortalStats, RiteStats, SettlementStats
from tests.tools.every_setup import ruled_realm, second_mortal, spirit, war_theatre
from tests.tools.factories import Realm, connect, make_entity

Ids = dict[str, int]
TREASURY = 500


async def teaching_spirit(session: AsyncSession, realm: Realm) -> Ids:
    found = await spirit(session, realm)
    elder = await make_entity(session, "Old Teacher", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=MortalStats())
    elder.status = EntityStatus.DEAD
    elder.end_epoch = 1
    rite = await make_entity(session, "Call of the Wisp", EntityType.RITE, world_id=realm.cosmos.world_id, stats=RiteStats())
    session.add(RiteProfileRow(rite_entity_id=rite.id, school=next(iter(MagicSchool)), source=MagicSource.LEY, requirements={}, cost={}, locked=[]))
    await connect(session, elder.id, rite.id, BondKind.OWNS)
    await connect(session, found["spirit"], elder.id, BondKind.DESCENDS_FROM)
    await session.flush()
    return {**found, "rite": rite.id}


async def host(session: AsyncSession, realm: Realm, name: str, owner: int, commander: int) -> int:
    army = await make_entity(session, name, EntityType.ARMY, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=ArmyStats(size=100))
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner, commander_entity_id=commander, raised_epoch=0))
    session.add(ArmyProfileRow(army_entity_id=army.id, region_entity_id=realm.cosmos.region_id))
    await session.flush()
    return army.id


async def armies_face(session: AsyncSession, realm: Realm) -> Ids:
    found = await war_theatre(session, realm)
    foe_leader = await second_mortal(session, realm)
    mine = await host(session, realm, "Vale Host", found["polity"], realm.mortal_id)
    foe = await host(session, realm, "Marsh Host", found["rival"], foe_leader["mortal"])
    return {**found, "army": mine, "foe": foe}


async def town_besieged(session: AsyncSession, realm: Realm) -> Ids:
    found = await armies_face(session, realm)
    war = await session.scalar(select(WarRow.id).order_by(WarRow.id.desc()).limit(1))
    assert war is not None
    town = await make_entity(
        session, "Marsh Hold", EntityType.SETTLEMENT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=SettlementStats()
    )
    session.add(SiegeRow(war_id=war, besieged_entity_id=town.id, besieger_entity_id=found["polity"], started_epoch=1, rounds=0, supplies=0))
    await session.flush()
    return {**found, "town": town.id}


async def rich_realm(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruled_realm(session, realm)
    profile = await session.get(PolityProfileRow, found["polity"])
    assert profile is not None
    profile.treasury = TREASURY
    await session.flush()
    return found
