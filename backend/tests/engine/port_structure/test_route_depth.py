from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.economy import TradeFlowRow, TradeRouteLossRow, TradeRouteProfileRow, TradeRouteTollRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTerritoryRow, PolityTreasuryRow
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, TradeLoss, TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import ClauseKind, DecisionRule, GovernmentKind, PartyRole, TreatyKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import BeastStats, PolityStats
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.chokepoints import contested_route, press_route_aims, route_grants, route_term
from aerona.engine.economy.control import close_route, open_route
from aerona.engine.economy.markets import market_nodes, quote_market
from aerona.engine.economy.route_backfill import ROUTE_FIXUP, route_backfill
from aerona.engine.economy.route_control import edit_route, found_by_hand, remove_toll, set_toll_stop
from aerona.engine.economy.route_dangers import Lairs, dangers_of, season_loss, season_pct_of, split
from aerona.engine.economy.routes import contacts, controllers, load_routes, set_tolls
from aerona.engine.economy.stocks import goods_of
from aerona.engine.economy.toll_polities import Realms
from aerona.engine.military.aims import set_aims
from aerona.engine.phases.commerce import trade_flow
from aerona.engine.phases.environment import environment_survey
from aerona.engine.phases.society_economy import default_society, save_society
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.treaties import sign
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def markets(session: AsyncSession, world: CoreWorld, rules: Rules) -> tuple[EntityRow, EntityRow]:
    first = await settlement(session, "Brennhold", world, world.regions[0], prosperity=60)
    second = await settlement(session, "Ashwick", world, world.regions[2], prosperity=20)
    for town in (first, second):
        await save_society(session, town.id, default_society(rules))
    return first, second


async def pairs(session: AsyncSession, first: EntityRow, second: EntityRow) -> list[TradeRouteProfileRow]:
    rows = await session.scalars(select(TradeRouteProfileRow))
    return [row for row in rows if {row.first_market_id, row.second_market_id} == {first.id, second.id}]


async def test_a_route_the_player_closed_is_never_founded_again_until_opened(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(trade_routes={"contact_hops": 5})
    first, second = await markets(session, world, rules)
    ctx = await manual_context(session, "test", rules)
    await goods_of(session, ctx.epoch).add(first.id, CommodityKind.GRAIN, 5000, GoodsFlow.PLAYER)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    await close_route(ctx, road.id)
    book = await EconomyBook.load(ctx)
    nodes = market_nodes(book)
    quotes = {node.id: await quote_market(ctx, book, node) for node in nodes}
    assert await contacts(ctx, book, nodes, await load_routes(ctx), quotes) == []
    for _ in range(3):
        await trade_flow(ctx)
    rows = await pairs(session, first, second)
    assert len(rows) == 1 and rows[0].status is TradeRouteStatus.CLOSED and rows[0].closed_by_player
    reopened = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    assert reopened.id == road.id
    rows = await pairs(session, first, second)
    assert len(rows) == 1 and rows[0].status is TradeRouteStatus.OPEN and not rows[0].closed_by_player


async def test_a_route_a_son_closed_is_honoured_too(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(trade_routes={"contact_hops": 5})
    first, second = await markets(session, world, rules)
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    profile = await session.get(TradeRouteProfileRow, road.id)
    assert profile is not None
    profile.status = TradeRouteStatus.CLOSED
    profile.closed_by_son_id = world.son.id
    await goods_of(session, ctx.epoch).add(first.id, CommodityKind.GRAIN, 5000, GoodsFlow.PLAYER)
    await trade_flow(ctx)
    assert len(await pairs(session, first, second)) == 1


async def surveyed(session: AsyncSession, rules: Rules) -> None:
    await environment_survey(await manual_context(session, "survey", rules))


async def test_beasts_bandits_and_weather_each_add_their_danger(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    await surveyed(session, rules)
    beast = await entity(session, "Graveljaw", EntityType.BEAST, BeastStats(danger=80), world_id=world.world.id, location_id=world.regions[1].id)
    profile = BeastProfileRow(beast_entity_id=beast.id, temper=BeastTemper.HUNGRY, hoard={}, locked=[])
    session.add(profile)
    path = [world.regions[0].id, world.regions[1].id, world.regions[2].id]
    ctx = await manual_context(session, "test", rules)
    calm = dangers_of(
        ctx, await EconomyBook.load(ctx), TradeMode.ROAD, path, await Lairs.load(ctx, await EconomyBook.load(ctx)), route_id=1, world_id=world.world.id
    )
    assert calm.bandits == 20
    assert calm.beasts == round(80 * rules.route_dangers.beast_danger_pct / 100)
    assert calm.beast_id == beast.id
    profile.temper = BeastTemper.TAMED
    book = await EconomyBook.load(ctx)
    assert dangers_of(ctx, book, TradeMode.ROAD, path, await Lairs.load(ctx, book), route_id=1, world_id=world.world.id).beasts == 0
    for region in path:
        session.add(ForcedWeatherRow(region_entity_id=region, world_id=world.world.id, from_epoch=1, until_epoch=999, kind=WeatherKind.BLIZZARD))
    await session.flush()
    book = await EconomyBook.load(ctx)
    stormy = dangers_of(ctx, book, TradeMode.ROAD, path, await Lairs.load(ctx, book), route_id=1, world_id=world.world.id)
    assert stormy.weather > calm.weather
    at_sea = dangers_of(ctx, book, TradeMode.SEA, path, await Lairs.load(ctx, book), route_id=1, world_id=world.world.id)
    assert at_sea.weather == 0 and at_sea.sea >= rules.route_dangers.sea_danger_base


def test_losses_are_split_by_their_share_of_the_danger() -> None:
    shares = split(10, {TradeLoss.BANDITS: 20, TradeLoss.BEASTS: 20, TradeLoss.WEATHER: 10, TradeLoss.SEA: 0}, TradeMode.ROAD)
    assert sum(shares.values()) == 10
    assert shares[TradeLoss.BANDITS] == 4 and shares[TradeLoss.BEASTS] == 4 and shares[TradeLoss.WEATHER] == 2
    assert split(5, {cause: 0 for cause in TradeLoss}, TradeMode.SEA) == {TradeLoss.SEA: 5}


def region(**values: object) -> RegionEnvironmentRow:
    base = {"temperature": 50, "seasonality": 100, "dominant_terrain": TerrainKind.PLAIN, "elevation_mean": 20}
    return RegionEnvironmentRow(**(base | values))


def season(**values: int) -> WorldSeasonRow:
    base = {"temperature_shift": 0, "rain_shift": 0, "travel": 100, "growth": 50, "campaign": 50, "position": 0}
    return WorldSeasonRow(**(base | values))


def test_every_way_of_travel_has_its_own_hard_season() -> None:
    rules = Rules()
    table = rules.route_seasons
    mild = season()
    assert all(season_loss(rules, mode, [region()], mild) == 0 for mode in TradeMode)
    muddy = season(travel=50)
    assert season_loss(rules, TradeMode.ROAD, [region()], muddy) == table.land_season_pct / 2
    winter = season(temperature_shift=-40)
    assert season_loss(rules, TradeMode.ROAD, [region(dominant_terrain=TerrainKind.MOUNTAINS)], winter) == table.pass_snow_pct
    assert season_loss(rules, TradeMode.ROAD, [region()], winter) == 0
    assert season_loss(rules, TradeMode.RIVER, [region()], winter) == table.river_ice_pct
    assert season_loss(rules, TradeMode.RIVER, [region()], season(rain_shift=40)) == table.river_flood_pct
    summer = season(temperature_shift=40)
    assert season_loss(rules, TradeMode.ROAD, [region(dominant_terrain=TerrainKind.DESERT)], summer) == table.caravan_heat_pct
    assert season_loss(rules, TradeMode.SKY, [region()], muddy) == table.sky_season_pct / 2
    assert season_loss(rules, TradeMode.SEA, [region()], muddy) == rules.trade_routes.sea_season_pct / 2


async def test_land_routes_are_seasonal_in_a_real_world(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    await surveyed(session, rules)
    ctx = await manual_context(session, "test", rules)
    book = await EconomyBook.load(ctx)
    for row in book.ground.seasons_of(world.world.id):
        row.travel = 40
    path = [item.id for item in world.regions]
    assert season_pct_of(rules, book, TradeMode.ROAD, path, world.world.id) < 100
    assert season_pct_of(rules, book, TradeMode.SKY, path, world.world.id) < 100


async def realm_over(session: AsyncSession, world: CoreWorld, region_id: int, control: int) -> EntityRow:
    polity = await entity(session, "Crown of Vale", EntityType.POLITY, PolityStats(legitimacy=50, stability=50), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=polity.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[]))
    session.add(PolityTerritoryRow(polity_entity_id=polity.id, region_entity_id=region_id, control=control))
    await session.flush()
    return polity


async def test_tolls_on_a_realms_land_fill_its_treasury(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(tolls={"default_rate_pct": 20}, market={"credit_threshold": 0, "credit_chance": 0})
    first, second = await markets(session, world, rules)
    polity = await realm_over(session, world, world.regions[1].id, 90)
    ctx = await manual_context(session, "test", rules)
    await goods_of(session, ctx.epoch).add(first.id, CommodityKind.GRAIN, 6000, GoodsFlow.PLAYER)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    await trade_flow(ctx)
    toll = await session.get(TradeRouteTollRow, (road.id, world.regions[1].id))
    assert toll is not None and toll.controller_entity_id == polity.id and toll.polity_entity_id == polity.id
    paid = await session.scalar(select(TradeFlowRow.toll_paid).where(TradeFlowRow.route_entity_id == road.id))
    entries = list(await session.scalars(select(PolityTreasuryRow).where(PolityTreasuryRow.polity_entity_id == polity.id)))
    assert paid and entries and all(entry.entry is TreasuryEntry.TOLLS for entry in entries)
    profile = await session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.treasury == sum(entry.amount for entry in entries) > 0


async def test_a_members_tolls_send_a_share_to_its_realm(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    town = await settlement(session, "Midway", world, world.regions[1])
    polity = await realm_over(session, world, world.regions[3].id, 90)
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    realms = await Realms.load(session)
    assert realms.treasury_of(town.id) == polity.id
    book = await EconomyBook.load(ctx)
    route = next(item for item in await load_routes(ctx) if item.entity.id == road.id)
    await set_tolls(ctx, book, route, await controllers(ctx, book, realms), realms=realms)
    assert route.tolls[world.regions[1].id].controller_entity_id == town.id
    assert route.tolls[world.regions[1].id].polity_entity_id == polity.id


async def test_route_wars_aim_at_the_road_and_the_victor_takes_its_tolls(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    rival = await settlement(session, "Tollgate", world, world.regions[1])
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    book = await EconomyBook.load(ctx)
    route = next(item for item in await load_routes(ctx) if item.entity.id == road.id)
    await set_tolls(ctx, book, route, await controllers(ctx, book))
    assert route.tolls[world.regions[1].id].controller_entity_id == rival.id
    assert await contested_route(session, first.id, rival.id) == road.id
    war = await open_war(ctx, first, rival, cause=WarCause.TRADE_ROUTE, cause_text="the way")
    await set_aims(ctx, war, first, rival)
    aim = await session.scalar(select(WarAimRow).where(WarAimRow.war_id == war.id, WarAimRow.kind == WarAimKind.SEIZE_ROUTE))
    assert aim is not None and aim.target_entity_id == road.id and aim.side_entity_id == first.id
    assert await press_route_aims(ctx, first.id, road.id) == 1
    assert aim.achieved == rules.chokepoints.blockade_aim_score
    aim.achieved = 100
    term = await route_term(ctx, war, aim, (first, rival), await RealmBook.load(session))
    assert term is not None and term[1].kind is ClauseKind.ROUTE_CONTROL
    assert route.profile.controller_entity_id == first.id
    await sign(ctx, TreatyKind.PEACE, [(first.id, PartyRole.SIGNATORY), (rival.id, PartyRole.SIGNATORY)], clauses=[term[1]], witnessed=False)
    grants = await route_grants(session)
    assert grants == {road.id: first.id}
    await set_tolls(ctx, book, route, await controllers(ctx, book), grants=grants)
    assert route.profile.controller_entity_id == first.id


async def test_held_route_values_stay_until_released(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    route = await edit_route(
        ctx, road.id, {"danger": 77, "danger_beasts": 33, "season_pct": 40, "capacity": 999, "mode": "sky", "controller_entity_id": second.id}, released=()
    )
    assert set(route.profile.locked) >= {"danger", "danger_beasts", "season_pct", "capacity", "mode", "controller_entity_id"}
    await trade_flow(ctx)
    profile = await session.get(TradeRouteProfileRow, road.id)
    assert profile is not None
    assert stat(road, "danger") == 77 and stat(road, "capacity") == 999
    assert profile.danger_beasts == 33 and profile.season_pct == 40 and profile.mode is TradeMode.SKY and profile.controller_entity_id == second.id
    await edit_route(ctx, road.id, {}, released=["danger", "season_pct"])
    await trade_flow(ctx)
    assert stat(road, "danger") != 77 and profile.season_pct != 40
    with pytest.raises(ValidationFailedError):
        await edit_route(ctx, road.id, {"danger": 300}, released=())


async def test_toll_stops_can_be_raised_held_and_forbidden(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    keeper = await settlement(session, "Bridgeward", world, world.regions[1])
    ctx = await manual_context(session, "test", rules)
    route = await found_by_hand(ctx, first.id, second.id, mode=TradeMode.ROAD, controller_id=keeper.id, toll_pct=12)
    assert route.profile.mode is TradeMode.ROAD and route.profile.controller_entity_id == keeper.id
    toll = await session.get(TradeRouteTollRow, (route.entity.id, world.regions[1].id))
    assert toll is not None and toll.rate_pct == 12 and toll.set_by_player and toll.controller_held
    await remove_toll(ctx, route.entity.id, world.regions[1].id)
    await trade_flow(ctx)
    assert await session.get(TradeRouteTollRow, (route.entity.id, world.regions[1].id)) is None
    await set_toll_stop(ctx, route.entity.id, world.regions[1].id, controller_id=keeper.id, rate=7, released=())
    toll = await session.get(TradeRouteTollRow, (route.entity.id, world.regions[1].id))
    assert toll is not None and toll.rate_pct == 7
    with pytest.raises(ValidationFailedError):
        await found_by_hand(ctx, first.id, second.id, mode=None, controller_id=None, toll_pct=None)


async def test_the_backfill_ledgers_past_tolls_and_aims_old_route_wars(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    polity = await realm_over(session, world, world.regions[1].id, 90)
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    session.add(TradeRouteTollRow(route_entity_id=road.id, region_entity_id=world.regions[1].id, controller_entity_id=polity.id, rate_pct=10))
    session.add(
        TradeFlowRow(
            route_entity_id=road.id, epoch=1, commodity=CommodityKind.GRAIN, from_entity_id=first.id, to_entity_id=second.id, volume=10, value=100, toll_paid=50
        )
    )
    await open_war(ctx, first, polity, cause=WarCause.TRADE_ROUTE, cause_text="old grudge over the road")
    await session.flush()
    result = await route_backfill(ctx, await Realms.load(session))
    assert result == {"polity_tolls": 50, "route_aims": 1}
    assert await session.get(AppliedFixupRow, ROUTE_FIXUP) is not None
    assert await route_backfill(ctx, await Realms.load(session)) == {}


async def test_beasts_carry_cargo_to_their_hoard(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(trade_routes={"danger_loss_pct": 100}, market={"credit_threshold": 0, "credit_chance": 0})
    rules = replace(rules, route_dangers=replace(rules.route_dangers, bandit_region_pct=0))
    first, second = await markets(session, world, rules)
    beast = await entity(session, "Graveljaw", EntityType.BEAST, BeastStats(danger=100), world_id=world.world.id, location_id=world.regions[1].id)
    profile = BeastProfileRow(beast_entity_id=beast.id, temper=BeastTemper.ENRAGED, hoard={}, locked=[])
    session.add(profile)
    ctx = await manual_context(session, "test", rules)
    await goods_of(session, ctx.epoch).add(first.id, CommodityKind.GRAIN, 6000, GoodsFlow.PLAYER)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    set_stats(road, danger=0)
    await trade_flow(ctx)
    losses = list(await session.scalars(select(TradeRouteLossRow).where(TradeRouteLossRow.route_entity_id == road.id)))
    assert losses and any(loss.cause is TradeLoss.BEASTS and loss.culprit_entity_id == beast.id for loss in losses)
    assert profile.hoard.get(CommodityKind.GRAIN.value, 0) > 0


async def test_a_route_the_god_lets_decay_ends_with_its_epoch_and_can_reopen(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    first, second = await markets(session, world, rules)
    ctx = await manual_context(session, "test", rules)
    road = await open_route(ctx, route_id=None, first_id=first.id, second_id=second.id)
    await edit_route(ctx, road.id, {"status": "decayed"}, released=())
    await session.flush()
    assert road.status is EntityStatus.DESTROYED and road.end_epoch is not None
    await edit_route(ctx, road.id, {"status": "open"}, released=())
    await session.flush()
    assert road.status is EntityStatus.CANON and road.end_epoch is None
