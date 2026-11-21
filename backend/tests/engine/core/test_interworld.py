from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow, OrbitalControlRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.urban import FleetRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.interworld import CampaignStage, MigrationCause, MigrationReception
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.travel import JourneyStatus, TravelMethod
from aerona.domain.enums.urban import TransportKind
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import ArmyStats, EventStats, PolityStats, SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.interworld.book import InterworldTally
from aerona.engine.interworld.campaigns import launch, tend_campaign
from aerona.engine.interworld.migrations import begin, count_arrivals, move
from aerona.engine.interworld.orbit import blockade, bombard
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, add_empty_world, entity, settlement, tuned_rules

GROWN = 3


def stage_of(campaign: InterworldCampaignRow) -> CampaignStage:
    return campaign.stage


async def crown(session: AsyncSession, world: CoreWorld, name: str, town: EntityRow) -> EntityRow:
    polity = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=town.world_id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=town.id, treasury=1000))
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


async def two_worlds(session: AsyncSession, world: CoreWorld) -> tuple[RouteRow, int, list[EntityRow]]:
    other, regions = await add_empty_world(session)
    route = RouteRow(
        world_a_id=world.world.id, world_b_id=other.id, method=TravelMethod.DIVINE_BRIDGE, duration_epochs=1, danger=0, created_epoch=0, capacity=100
    )
    session.add(route)
    await session.flush()
    return route, other.id, regions


async def host_of(session: AsyncSession, world: CoreWorld, owner: EntityRow, size: int) -> EntityRow:
    army = await entity(session, f"{owner.name} Host", EntityType.ARMY, ArmyStats(size=size), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner.id, raised_epoch=0))
    session.add(ArmyProfileRow(army_entity_id=army.id, region_entity_id=world.regions[0].id, baggage=0, supply_line=[], locked=[]))
    await session.flush()
    return army


async def test_a_campaign_carries_what_its_carriers_bear_and_loses_some_on_the_crossing(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    route, target, _regions = await two_worlds(session, world)
    attacker = await crown(session, world, "The Reaching Crown", await settlement(session, "Launchport", world, world.regions[0]))
    session.add(FleetRow(owner_entity_id=attacker.id, kind=TransportKind.SPACE, count=5, locked=[]))
    army = await host_of(session, world, attacker, 5000)
    tally = InterworldTally()
    row = await launch(ctx, attacker, army, target, route, tally=tally)
    per = ctx.rules.interworld.carrier_people_per_capacity
    assert row.forces == min(5000, 5 * per + route.capacity * per // 10) and row.stage is CampaignStage.TRANSIT
    await tend_campaign(ctx, row, tally)
    assert stage_of(row) is CampaignStage.SUPREMACY and row.forces < min(5000, row.capacity) and tally.lost_in_transit > 0


async def test_a_won_orbit_lets_a_host_land_and_a_lost_one_starves_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "landing", tuned_rules(interworld={"landing_needs_control_pct": 5, "supply_decay_per_hop": 80}))
    route, target, regions = await two_worlds(session, world)
    attacker = await crown(session, world, "The Landing Crown", await settlement(session, "Shipyard", world, world.regions[0]))
    army = await host_of(session, world, attacker, 1000)
    tally = InterworldTally()
    row = await launch(ctx, attacker, army, target, route, tally=tally)
    row.stage = CampaignStage.SUPREMACY
    await tend_campaign(ctx, row, tally)
    assert row.stage is CampaignStage.LANDING and tally.orbits_won == 1
    await tend_campaign(ctx, row, tally)
    assert stage_of(row) is CampaignStage.HOLDING and army.world_id == target and army.location_id in {region.id for region in regions}
    orbit = await session.scalar(select(OrbitalControlRow).where(OrbitalControlRow.world_id == target))
    assert orbit is not None
    await session.delete(orbit)
    await session.flush()
    supplied = row.supply
    await tend_campaign(ctx, row, tally)
    assert row.supply < supplied and row.forces < 1000
    await tend_campaign(ctx, row, tally)
    assert stage_of(row) is CampaignStage.WITHDRAWN and tally.withdrawn == 1


async def test_the_holder_of_an_orbit_strikes_the_enemy_below_and_tolls_the_ways(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    route, _target, _regions = await two_worlds(session, world)
    town = await settlement(session, "Underfire", world, world.regions[1], population=6000)
    holder = await crown(session, world, "The Sky Crown", await settlement(session, "Skyhold", world, world.regions[2]))
    event = await entity(session, "The Sky War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOSTILITY, started_epoch=0)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=holder.id, side=WarSide.ATTACKER, joined_epoch=0))
    session.add(WarSideRow(war_id=war.id, entity_id=town.id, side=WarSide.DEFENDER, joined_epoch=0))
    orbit = OrbitalControlRow(world_id=world.world.id, holder_entity_id=holder.id, strength=80, locked=[])
    session.add(orbit)
    await session.flush()
    people = stat(town, "population") or 0
    tally = InterworldTally()
    await bombard(ctx, orbit, tally)
    assert (stat(town, "population") or 0) < people and tally.bombardments == 1
    await blockade(ctx, orbit)
    assert route.toll_controller_entity_id == holder.id and route.toll_pct >= ctx.rules.interworld.blockade_toll_pct


async def test_a_people_moves_to_another_world_by_journeys_and_their_arrival_is_counted(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    route, target, _regions = await two_worlds(session, world)
    town = await settlement(session, "Crowdhold", world, world.regions[0], population=8000)
    town.civ_tier = GROWN
    tally = InterworldTally()
    row = await begin(ctx, town, target, MigrationCause.LAND_HUNGER, route, tally=tally)
    assert row.reception is MigrationReception.WELCOME and row.per_epoch > 0
    await move(ctx, row, town, tally)
    assert row.moved > 0 and (stat(town, "population") or 0) == 8000 - row.moved and len(row.journey_ids) == 1
    journey = await session.get(JourneyRow, row.journey_ids[0])
    assert journey is not None and journey.destination_world_id == target
    journey.status = JourneyStatus.ARRIVED
    await count_arrivals(ctx, row, tally)
    assert row.arrived == journey.population and row.journey_ids == []


async def test_a_world_at_war_with_the_movers_refuses_them(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    route, target, regions = await two_worlds(session, world)
    town = await settlement(session, "Fleeing Town", world, world.regions[0], population=3000)
    town.civ_tier = GROWN
    far = await entity(session, "Far Seat", EntityType.SETTLEMENT, SettlementStats(population=900), world_id=target, location_id=regions[0].id)
    host = await crown(session, world, "The Closed Crown", far)
    event = await entity(session, "The Closing War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOSTILITY, started_epoch=0)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=host.id, side=WarSide.ATTACKER, joined_epoch=0))
    session.add(WarSideRow(war_id=war.id, entity_id=town.id, side=WarSide.DEFENDER, joined_epoch=0))
    await session.flush()
    tally = InterworldTally()
    row = await begin(ctx, town, target, MigrationCause.FLIGHT, route, tally=tally)
    assert row.reception is MigrationReception.REFUSAL
    await move(ctx, row, town, tally)
    assert row.moved == 0 and row.waiting == row.per_epoch and tally.refused == 1
    assert await session.scalar(select(InterworldMigrationRow.id)) == row.id
    assert await session.scalar(select(InterworldCampaignRow.id)) is None
