import pytest

from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import FactionStats, ResourceStats
from aerona.engine.phases.trade import barter_and_rivalry, currency, impose_trade, order_minting, trade_income
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, knowledge, link, make, named, people, settlement, tuned


async def test_routes_bring_prosperity_and_wealth(realm: Realm) -> None:
    first = await people(realm, "Ama", prosperity=30, wealth=30)
    second = await people(realm, "Bel", prosperity=30, wealth=30)
    await link(realm.session, first.id, second.id, BondKind.TRADES_WITH)
    trading = await knowledge(realm, "Barter", KnowledgeBranch.TRADE)
    await link(realm.session, first.id, trading.id, BondKind.KNOWS)
    ctx = context(realm.session)
    await trade_income(ctx)
    settings = ctx.rules.trade
    assert stat(first, "prosperity") == 30 + min(settings.route_prosperity * settings.knowledge_mult, settings.prosperity_cap)
    assert stat(second, "prosperity") == 30 + settings.route_prosperity
    assert stat(second, "wealth") == 30 + settings.route_wealth


async def test_different_resources_open_barter(realm: Realm) -> None:
    first = await settlement(realm, "Saltby")
    second = await settlement(realm, "Copperton")
    salt = await make(realm.session, "Salt Pan", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=realm.world.id, location_id=realm.region.id)
    copper = await make(realm.session, "Copper Vein", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, first.id, salt.id, BondKind.OWNS)
    await link(realm.session, second.id, copper.id, BondKind.OWNS)
    ctx = context(realm.session, tuned(trade={"barter_chance": 100}))
    await barter_and_rivalry(ctx)
    assert await bonded(realm.session, first.id, second.id, BondKind.TRADES_WITH)
    assert "trade.barter" in await chronicle_keys(realm.session)


async def test_same_resources_breed_rivalry(realm: Realm) -> None:
    first = await settlement(realm, "Eastwell")
    second = await settlement(realm, "Westwell")
    spring = await make(realm.session, "Spring", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, first.id, spring.id, BondKind.OWNS)
    await link(realm.session, second.id, spring.id, BondKind.OWNS)
    ctx = context(realm.session, tuned(trade={"rivalry_war_chance": 100}))
    await barter_and_rivalry(ctx)
    assert await bonded(realm.session, first.id, second.id, BondKind.ENEMY)


async def test_minting_adoption_and_shared_coin(realm: Realm) -> None:
    minter = await settlement(realm, "Mint", prosperity=90)
    partner = await settlement(realm, "Buyer", prosperity=40)
    trading = await knowledge(realm, "Coinage", KnowledgeBranch.TRADE)
    await link(realm.session, minter.id, trading.id, BondKind.KNOWS)
    await link(realm.session, minter.id, partner.id, BondKind.TRADES_WITH)
    ctx = context(realm.session, tuned(trade={"coinage_chance": 100, "currency_adopt_chance": 100}))
    await currency(ctx)
    coins = [item for item in await named(realm.session, EntityType.ITEM) if item.engine_kind is EngineKind.CURRENCY]
    assert len(coins) == 1
    assert await bonded(realm.session, partner.id, coins[0].id, BondKind.OWNS)
    before = stat(partner, "prosperity") or 0
    await currency(context(realm.session, tuned(trade={"coinage_chance": 0}), epoch=4))
    assert (stat(partner, "prosperity") or 0) > before


async def test_manual_trade_and_minting(realm: Realm) -> None:
    first = await settlement(realm, "Port")
    guild = await make(realm.session, "Guild", EntityType.FACTION, FactionStats(strength=20, wealth=80), world_id=realm.world.id, location_id=first.id)
    ctx = context(realm.session)
    assert await impose_trade(ctx, first.id, guild.id)
    assert not await impose_trade(ctx, first.id, guild.id)
    coin = await order_minting(ctx, guild.id)
    assert coin.engine_kind is EngineKind.CURRENCY
    with pytest.raises(ValidationFailedError):
        await order_minting(ctx, guild.id)
