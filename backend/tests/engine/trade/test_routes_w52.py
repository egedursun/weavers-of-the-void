import importlib
import pkgutil

from sqlalchemy import select

import aerona.domain.enums as enum_package
from aerona.catalog.carriers import CARRIERS
from aerona.catalog.kinds.trade_modes import NAVIGATED_MODES, TRADE_LOSS_CULPRITS, TRADE_LOSSES, TRADE_MODES
from aerona.catalog.life.economy import DANGER_KEYS, LIVE
from aerona.catalog.life_traits import CARRYING_ROUTES
from aerona.catalog.means import AIDS, CONTAINERS, aid_cut, container_capacity
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.economy import TradeLoss, TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.means import ContainerKind, NavigationAid
from aerona.domain.enums.operations import CarrierKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.economy.route_dangers import Dangers, split, weather_weight
from aerona.engine.economy.route_states import take_officials, weigh_contest
from aerona.engine.economy.routes import carrier_share, season_factor
from aerona.rules.registry import Rules
from aerona.services.books.typed import TypedIndex
from aerona.services.integrity.w52_agent_b import misfit_carriers, open_unseasoned, unload_carrier, unseasoned_routes
from tests.engine.society.factories import Realm, context, make, tuned
from tests.engine.trade.helpers import lay_route, seasons_of


def test_route_environment_is_gone_and_the_media_are_one_taxonomy() -> None:
    for module in pkgutil.iter_modules(enum_package.__path__):
        assert not hasattr(importlib.import_module(f"aerona.domain.enums.{module.name}"), "RouteEnvironment")
    assert set(TRADE_MODES) == set(TradeMode) and len(TradeMode) == 8
    assert "caravan" not in {mode.value for mode in TradeMode}
    assert TradeMode.ROAD in CARRIERS[CarrierKind.PACK_ANIMALS].modes
    assert set(NAVIGATED_MODES) == {TradeMode.SEA, TradeMode.SKY}


def test_every_state_loss_container_and_aid_has_its_catalogue() -> None:
    assert TradeRouteStatus.CONTESTED in CARRYING_ROUTES and TradeRouteStatus.SEASONAL in CARRYING_ROUTES and TradeRouteStatus.SEASONAL in LIVE
    assert set(DANGER_KEYS) == set(TradeLoss) == set(TRADE_LOSSES) == set(TRADE_LOSS_CULPRITS)
    assert TRADE_LOSS_CULPRITS[TradeLoss.OFFICIALS] == "official_id"
    rules = Rules()
    for kind in ContainerKind:
        assert CONTAINERS[kind].suits and container_capacity(rules, kind) > 0
    assert container_capacity(rules, ContainerKind.TANK) > container_capacity(rules, ContainerKind.SKIN)
    for aid in NavigationAid:
        assert aid_cut(rules, aid) > 0
    assert AIDS[NavigationAid.POSITIONING].networked and AIDS[NavigationAid.WAYFINDING].needs is None and AIDS[NavigationAid.BEACONS].shore_works


def test_the_new_losses_take_their_share_and_the_old_are_reckoned_by_their_rules() -> None:
    rules = tuned(route_dangers={"bandits_pct": 50})
    dangers = Dangers(bandits=20, officials=10, spoilage=10, pilferage=10).reckon(rules)
    assert dangers.bandits == 10 and dangers.officials == 10
    shares = split(40, dangers.parts(), TradeMode.ROAD)
    assert set(shares) == {TradeLoss.BANDITS, TradeLoss.OFFICIALS, TradeLoss.SPOILAGE, TradeLoss.PILFERAGE} and sum(shares.values()) == 40
    assert dangers.total == 40


async def test_a_seasonal_route_loses_its_closed_season(realm: Realm) -> None:
    route = await lay_route(realm, status=TradeRouteStatus.SEASONAL)
    await seasons_of(realm, "Thaw", "High Sun", "Fall", "Deep Cold")
    route.profile.season_pct = 80
    assert season_factor(route, 4) == 0.8
    route.profile.closed_season = 3
    assert abs(season_factor(route, 4) - 0.6) < 1e-9
    assert carrier_share(Rules(), CarrierKind.PACK_ANIMALS) < 1 == carrier_share(Rules(), None)


async def test_corrupt_ends_take_their_officials_share_and_war_contests_the_route(realm: Realm) -> None:
    ctx = context(realm.session)
    route = await lay_route(realm)
    crowns = []
    for index, end in enumerate(route.ends):
        crown = await make(realm.session, f"Crown {index}", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
        realm.session.add_all(
            [
                PolityMemberRow(polity_entity_id=crown.id, member_entity_id=end),
                PolityProfileRow(
                    polity_entity_id=crown.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), corruption=40 + index * 40
                ),
            ]
        )
        crowns.append(crown.id)
    await realm.session.flush()
    dangers = Dangers()
    await take_officials(ctx, route, dangers)
    assert dangers.officials == ctx.rules.route_dangers.officials_pct * 80 // 100 == route.profile.danger_officials
    assert dangers.official_id == crowns[1]
    await weigh_contest(ctx, route, {(crowns[0], crowns[1])})
    assert route.profile.status is TradeRouteStatus.CONTESTED
    assert await realm.session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "route.contested")) is not None
    await weigh_contest(ctx, route, set())
    assert route.profile.status is TradeRouteStatus.OPEN


async def test_integrity_opens_an_unseasoned_route_and_unloads_a_misfit_carrier(realm: Realm) -> None:
    route = await lay_route(realm, status=TradeRouteStatus.SEASONAL)
    route.profile.carrier = CarrierKind.SEA
    await realm.session.flush()
    assert await unseasoned_routes(realm.session) == [route.entity.id]
    assert await misfit_carriers(realm.session) == [route.entity.id]
    await open_unseasoned(realm.session, route.entity.id)
    await unload_carrier(realm.session, route.entity.id)
    assert route.profile.status is TradeRouteStatus.OPEN and route.profile.carrier is None


async def test_the_book_and_codex_name_a_route_closed_season(realm: Realm) -> None:
    route = await lay_route(realm, status=TradeRouteStatus.SEASONAL)
    await seasons_of(realm, "Thaw", "Deep Cold")
    route.profile.closed_season = 1
    await realm.session.flush()
    index = await TypedIndex.load(realm.session, {})
    rows = [fact for section in index.of(route.entity.id) for fact in [*section.rows, *(f"{item.label}: {item.value}" for item in section.facts)]]
    assert any("Closed season: Deep Cold" in row for row in rows), rows


def test_pack_animals_on_an_arid_road_feel_the_weather_by_the_caravan_rule() -> None:
    rules = Rules()
    desert = [RegionEnvironmentRow(entity_id=1, world_id=1, dominant_terrain=TerrainKind.DESERT)]
    meadow = [RegionEnvironmentRow(entity_id=2, world_id=1, dominant_terrain=TerrainKind.PLAIN)]
    road = int(getattr(rules.route_dangers, TRADE_MODES[TradeMode.ROAD].weather_rule))
    assert weather_weight(rules, TradeMode.ROAD, CarrierKind.PACK_ANIMALS, desert) == rules.route_dangers.caravan_weather_pct
    assert weather_weight(rules, TradeMode.ROAD, CarrierKind.PACK_ANIMALS, meadow) == road
    assert weather_weight(rules, TradeMode.ROAD, None, desert) == road
