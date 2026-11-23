from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, CaptiveCohortRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import CaptiveFate, Stance, UnitKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import ArmyStats, EventStats
from tests.tools.every_setup import ruler, second_mortal, second_settlement
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm, make_entity


async def host(session: AsyncSession, realm: Realm, name: str = "Vale Host") -> int:
    army = await make_entity(session, name, EntityType.ARMY, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=ArmyStats(size=100))
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=realm.settlement_id, commander_entity_id=realm.mortal_id, raised_epoch=0))
    session.add(
        ArmyProfileRow(army_entity_id=army.id, region_entity_id=realm.cosmos.region_id, stance=Stance.MARCH, doctrine="shieldwall", supply_line=[], locked=[])
    )
    session.add(ArmyUnitRow(army_entity_id=army.id, kind=UnitKind.LEVY, count=100, locked=[]))
    await session.flush()
    return army.id


async def war_host(session: AsyncSession, realm: Realm) -> Ids:
    other = await second_mortal(session, realm)
    return {"army": await host(session, realm), **other}


async def war_with(session: AsyncSession, realm: Realm) -> tuple[int, int]:
    town = (await second_settlement(session, realm))["settlement"]
    event = await make_entity(session, "The Ford War", EntityType.EVENT, world_id=realm.cosmos.world_id, stats=EventStats())
    war = WarRow(event_entity_id=event.id, world_id=realm.cosmos.world_id, cause=next(iter(WarCause)), started_epoch=1)
    session.add(war)
    await session.flush()
    return war.id, town


async def besieging(session: AsyncSession, realm: Realm) -> Ids:
    war_id, town = await war_with(session, realm)
    await host(session, realm)
    inside = await make_entity(session, "Gate Warden", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=town)
    siege = SiegeRow(war_id=war_id, besieged_entity_id=town, besieger_entity_id=realm.settlement_id, started_epoch=1, works={}, locked=[])
    session.add(siege)
    await session.flush()
    return {"siege": siege.id, "inside": inside.id, "settlement": town}


async def besieged_home(session: AsyncSession, realm: Realm) -> Ids:
    war_id, town = await war_with(session, realm)
    siege = SiegeRow(war_id=war_id, besieged_entity_id=realm.settlement_id, besieger_entity_id=town, started_epoch=1, works={}, locked=[])
    session.add(siege)
    await session.flush()
    return {"siege": siege.id}


async def held_captives(session: AsyncSession, realm: Realm) -> Ids:
    war_id, town = await war_with(session, realm)
    row = CaptiveCohortRow(
        captor_entity_id=realm.settlement_id,
        origin_entity_id=town,
        war_id=war_id,
        count=40,
        social_class=SocialClass.FARMER,
        fate=CaptiveFate.HELD,
        since_epoch=1,
    )
    session.add(row)
    await session.flush()
    return {"cohort": row.id}


async def spymaster_post(session: AsyncSession, realm: Realm) -> Ids:
    found = await ruler(session, realm)
    session.add(PolityMemberRow(polity_entity_id=found["polity"], member_entity_id=realm.settlement_id, locked=[]))
    session.add(OfficeRow(polity_entity_id=found["polity"], kind=OfficeKind.SPYMASTER, holder_entity_id=realm.mortal_id))
    town = (await second_settlement(session, realm))["settlement"]
    mark = await make_entity(session, "Lowmere Clerk", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=town)
    await session.flush()
    return {**found, "settlement": town, "mortal": mark.id}


async def crowned(session: AsyncSession, realm: Realm) -> Ids:
    return await ruler(session, realm)
