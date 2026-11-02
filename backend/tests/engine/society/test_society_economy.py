from dataclasses import replace
from typing import Any

import pytest

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.economy import ResourceCommodityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.domain.enums.world import ClimateEra
from aerona.domain.models.entity_stats import ResourceStats
from aerona.engine.phases.society_economy import (
    EconomyInputs,
    class_targets,
    default_society,
    food_rate,
    incite_class_uprising,
    market_prices,
    normalized_shares,
    order_forge,
    satisfaction_targets,
    send_famine,
    send_plenty,
    set_class_shares,
    set_resource_commodity,
    set_stores,
    society_economy,
    society_of,
    society_view,
)
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, active_bonds, bonded, chronicle_keys, context, knowledge, link, make, named, settlement, tuned

RULES = Rules()


BASE_INPUTS = EconomyInputs(
    climate=ClimateEra.TEMPERATE,
    at_war=False,
    routes=0,
    pays_tribute=False,
    has_god=True,
    godless=False,
    cursed=False,
    bounty_law=False,
    justice=None,
    fertility=50,
    branches=frozenset(),
    ore_income=0.0,
    piety=50,
    prosperity=50,
    skilled_crafts=False,
)


def inputs(**changes: Any) -> EconomyInputs:
    return replace(BASE_INPUTS, **changes)


def test_shares_normalise_to_a_hundred() -> None:
    shares = normalized_shares({SocialClass.FARMER: 2.0, SocialClass.WARRIOR: 2.0})
    assert shares[SocialClass.FARMER] == 50.0
    assert shares[SocialClass.SCRIBE] == 0.0
    assert round(sum(normalized_shares(default_society(RULES).shares).values())) == 100


def test_class_targets_follow_knowledge_war_and_godlessness() -> None:
    base = class_targets(RULES, inputs())
    farming = class_targets(RULES, inputs(branches=frozenset({KnowledgeBranch.AGRICULTURE})))
    assert farming[SocialClass.FARMER] > base[SocialClass.FARMER]
    assert class_targets(RULES, inputs(at_war=True))[SocialClass.WARRIOR] > base[SocialClass.WARRIOR]
    assert class_targets(RULES, inputs(godless=True))[SocialClass.PRIEST] < base[SocialClass.PRIEST]
    assert class_targets(RULES, inputs(routes=3))[SocialClass.MERCHANT] > base[SocialClass.MERCHANT]


def test_food_rate_reacts_to_climate_and_law() -> None:
    settings = RULES.society
    temperate = food_rate(settings, inputs(), 55.0)
    assert food_rate(settings, inputs(climate=ClimateEra.DROUGHT), 55.0) < temperate
    assert food_rate(settings, inputs(bounty_law=True), 55.0) > temperate
    assert food_rate(settings, inputs(), 0.0) == settings.food_rate_min_pct / 100


def test_prices_rise_in_scarcity() -> None:
    settings = RULES.society
    scarce = market_prices(settings, 1.0, {Commodity.FOOD: 10, Commodity.ORE: 1, Commodity.GOODS: 1})
    plenty = market_prices(settings, 1.0, {Commodity.FOOD: 190, Commodity.ORE: 100, Commodity.GOODS: 200})
    assert scarce[Commodity.FOOD] > plenty[Commodity.FOOD]
    assert scarce[Commodity.ORE] > plenty[Commodity.ORE]
    assert plenty[Commodity.GOODS] >= settings.price_min_pct


def test_satisfaction_targets_punish_hunger_tribute_and_reward_justice() -> None:
    stocks = {Commodity.FOOD: 100, Commodity.ORE: 50, Commodity.GOODS: 50}
    hungry = {**stocks, Commodity.FOOD: 0}
    calm = satisfaction_targets(RULES, inputs(), stocks)
    assert satisfaction_targets(RULES, inputs(), hungry)[SocialClass.FARMER] < calm[SocialClass.FARMER]
    assert satisfaction_targets(RULES, inputs(pays_tribute=True), stocks)[SocialClass.SCRIBE] < calm[SocialClass.SCRIBE]
    assert satisfaction_targets(RULES, inputs(justice=100), stocks)[SocialClass.SCRIBE] > calm[SocialClass.SCRIBE]


async def test_phase_creates_societies_and_moves_stocks(realm: Realm) -> None:
    town = await settlement(realm, "Harrow")
    ctx = context(realm.session)
    await society_economy(ctx)
    row = await realm.session.get(CommunitySocietyRow, town.id)
    assert row is not None
    assert row.stock(Commodity.FOOD) != RULES.society.initial_food
    assert ctx.environment.stats.counters["test.communities"] == 1


async def test_famine_strikes_empty_granaries(realm: Realm) -> None:
    town = await settlement(realm, "Gaunt", population=4000)
    rules = tuned(society={"famine_food": 1000, "famine_rate_pct": 1000, "food_rate_effect": 0})
    ctx = context(realm.session, rules)
    await society_economy(ctx)
    assert stat(town, "population") == 4000 * rules.society.famine_population_kept_pct // 100
    assert "society.famine" in await chronicle_keys(realm.session)


async def test_forges_and_ore_mines(realm: Realm) -> None:
    town = await settlement(realm, "Anvil")
    smithing = await knowledge(realm, "Smithing", KnowledgeBranch.METALLURGY)
    await link(realm.session, town.id, smithing.id, BondKind.KNOWS)
    mine = await make(realm.session, "Iron Hill", EntityType.RESOURCE, ResourceStats(abundance=100), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, town.id, mine.id, BondKind.OWNS)
    ctx = context(realm.session, tuned(society={"weapon_ore_required": 0, "weapon_warrior_pct": 0, "forge_weapon_chance": 100}))
    await set_resource_commodity(ctx, mine.id, Commodity.ORE)
    assert (await realm.session.get(ResourceCommodityRow, mine.id)) is not None
    await society_economy(ctx)
    weapons = [item for item in await named(realm.session, EntityType.ITEM) if item.subtype == "weapon"]
    assert len(weapons) == 1
    assert await bonded(realm.session, town.id, weapons[0].id, BondKind.OWNS)


async def test_class_uprising_starts_a_civil_war(realm: Realm) -> None:
    town = await settlement(realm, "Riot", population=5000)
    ctx = context(realm.session, tuned(society={"revolt_satisfaction": 101, "class_revolt_chance": 100, "revolt_min_population": 0}))
    await society_economy(ctx)
    factions = await named(realm.session, EntityType.FACTION)
    assert len(factions) == 1
    assert factions[0].engine_kind is EngineKind.REBELS
    assert factions[0].social_class is not None
    assert await bonded(realm.session, factions[0].id, town.id, BondKind.ENEMY)


async def test_bankruptcy_hits_merchants_without_routes(realm: Realm) -> None:
    town = await settlement(realm, "Ledger", prosperity=10)
    ctx = context(realm.session, tuned(society={"bankruptcy_merchant_pct": 0, "guild_bankruptcy_chance": 100, "bankruptcy_prosperity": 100}))
    await society_economy(ctx)
    assert "society.bankruptcy" in await chronicle_keys(realm.session)
    assert (stat(town, "prosperity") or 0) < 10


async def test_trade_flows_level_stores(realm: Realm) -> None:
    rich = await settlement(realm, "Granary")
    poor = await settlement(realm, "Hollow")
    ctx = context(realm.session)
    await set_stores(ctx, rich.id, {Commodity.FOOD: 190})
    await set_stores(ctx, poor.id, {Commodity.FOOD: 0})
    await link(realm.session, rich.id, poor.id, BondKind.TRADES_WITH)
    await society_economy(ctx)
    rich_food = (await society_of(realm.session, RULES, rich.id)).stocks[Commodity.FOOD]
    poor_food = (await society_of(realm.session, RULES, poor.id)).stocks[Commodity.FOOD]
    assert rich_food - poor_food < 190
    assert ctx.environment.stats.counters["test.trade_flows"] == 1


async def test_manual_controls(realm: Realm) -> None:
    town = await settlement(realm, "Decree", population=6000)
    ctx = context(realm.session)
    shares = await set_class_shares(ctx, town.id, {SocialClass.WARRIOR: 200.0})
    assert shares.shares[SocialClass.WARRIOR] > 50
    with pytest.raises(ValidationFailedError):
        await set_stores(ctx, town.id, {Commodity.FOOD: -1})
    await set_stores(ctx, town.id, {Commodity.ORE: 0})
    with pytest.raises(ValidationFailedError):
        await order_forge(ctx, town.id)
    await set_stores(ctx, town.id, {Commodity.ORE: 50})
    weapon = await order_forge(ctx, town.id)
    assert await active_bonds(realm.session, town.id, BondKind.OWNS)
    assert weapon.entity_type is EntityType.ITEM
    famine = await send_famine(ctx, town.id)
    assert famine.stocks[Commodity.FOOD] == 0
    plenty = await send_plenty(ctx, town.id)
    assert plenty.stocks[Commodity.FOOD] == RULES.society.stockpile_cap
    view = await society_view(realm.session, RULES, town.id)
    assert view.stored
    rebels = await incite_class_uprising(ctx, town.id, SocialClass.FARMER)
    assert rebels.social_class is SocialClass.FARMER
