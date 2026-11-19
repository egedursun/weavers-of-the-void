from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import AgeGrade
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.youth import YouthPurpose
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import set_stats
from aerona.engine.youth.groups import keep_youth
from aerona.engine.youth.seed import seed_youth
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def home_town(session: AsyncSession, world: CoreWorld) -> EntityRow:
    if "town" not in world.extra:
        town = await settlement(session, "Ardun", world, world.regions[0], prosperity=20)
        await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
        session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, public_order=20, crime=10, locked=[], foreigners={}))
        session.add(YouthStandingRow(people_entity_id=world.people.id, youth_from=12, youth_to=20, locked=[]))
        await session.flush()
        world.extra["town"] = town
    town = world.extra["town"]
    assert isinstance(town, EntityRow)
    return town


async def youths(session: AsyncSession, world: CoreWorld, *names: str, age: int = 15) -> list[EntityRow]:
    town = await home_town(session, world)
    return [await mortal(session, name, world, town.id, age=age) for name in names]


async def group_of(session: AsyncSession, world: CoreWorld, purpose: YouthPurpose, members: list[EntityRow]) -> YouthGroupRow:
    town = await home_town(session, world)
    group = YouthGroupRow(settlement_entity_id=town.id, name="the youth of the ford", purpose=purpose, leader_node_id=members[0].id, locked=[])
    session.add(group)
    await session.flush()
    session.add_all(YouthGroupMemberRow(group_id=group.id, member_node_id=being.id, locked=[]) for being in members)
    await session.flush()
    return group


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(youth=values)))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("youth.")).order_by(IncidentRow.id)))


async def test_youths_gather_into_a_group_and_leave_it_when_they_come_of_age(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    gathered = await youths(session, world, "Ama", "Kel", "Iro")
    tally = await keep_youth(tuned(ctx, delinquency_base_pct=0, service_cooption_pct=0))
    group = await session.scalar(select(YouthGroupRow))
    assert group is not None and tally.formed == 1 and tally.joined == 3
    set_stats(gathered[0], age=25)
    await session.flush()
    await keep_youth(tuned(ctx, delinquency_base_pct=0, service_cooption_pct=0))
    assert await session.get(YouthGroupMemberRow, (group.id, gathered[0].id)) is None
    assert await session.get(YouthGroupMemberRow, (group.id, gathered[1].id)) is not None
    assert {"youth.group_formed", "youth.came_of_age"} <= set(await kinds_of(session))


async def test_a_group_of_mischief_in_a_poor_disordered_town_makes_trouble(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await group_of(session, world, YouthPurpose.MISCHIEF, await youths(session, world, "Dun", "Pell"))
    tally = await keep_youth(tuned(ctx, delinquency_base_pct=100, service_cooption_pct=0, group_effect=0))
    town = await home_town(session, world)
    profile = await session.get(SettlementProfileRow, town.id)
    assert tally.delinquent == 1 and profile is not None and profile.crime > 10
    assert "youth.delinquency" in await kinds_of(session)


async def test_gangs_draw_youths_of_crime_and_a_realm_draws_them_into_service(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    members = await youths(session, world, "Vael", "Orin")
    group = await group_of(session, world, YouthPurpose.CRIME, members)
    town = await home_town(session, world)
    gang = await entity(session, "The Ash Hand", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=gang.id, kind=FactionKind.CRIME_FAMILY, locked=[]))
    boss = await mortal(session, "Grell", world, town.id, age=40)
    session.add(FactionMembershipRow(faction_entity_id=gang.id, mortal_entity_id=boss.id, locked=[]))
    await session.flush()
    tally = await keep_youth(tuned(ctx, delinquency_base_pct=0, recruitment_pct=100, service_cooption_pct=0))
    assert tally.recruited == 2 and await session.get(FactionMembershipRow, (gang.id, members[0].id)) is not None
    realm = await entity(session, "Crown of Ardun", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[], emblem={}))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    await session.flush()
    await keep_youth(tuned(ctx, delinquency_base_pct=0, recruitment_pct=0, service_cooption_pct=100))
    assert group.purpose is YouthPurpose.SERVICE


async def test_youth_age_sets_become_youth_groups(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    members = await youths(session, world, "Lir", "Sora")
    age_set = AgeSetRow(people_entity_id=world.people.id, name="Those of the Long Rains", grade=AgeGrade.YOUTHS, locked=[])
    session.add(age_set)
    await session.flush()
    session.add_all(AgeSetMemberRow(mortal_entity_id=being.id, age_set_id=age_set.id, locked=[]) for being in members)
    await session.flush()
    tally = await seed_youth(ctx)
    group = await session.scalar(select(YouthGroupRow).where(YouthGroupRow.age_set_id == age_set.id))
    assert tally.groups == 1 and group is not None and group.name == age_set.name
    assert await session.get(YouthGroupMemberRow, (group.id, members[1].id)) is not None


async def test_a_group_of_defence_keeps_watch(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await group_of(session, world, YouthPurpose.DEFENCE, await youths(session, world, "Bel", "Tal"))
    await keep_youth(tuned(ctx, delinquency_base_pct=0, service_cooption_pct=0, group_effect=4))
    profile = await session.get(SettlementProfileRow, (await home_town(session, world)).id)
    assert profile is not None and profile.crime == 6
