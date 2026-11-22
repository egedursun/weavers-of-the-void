import pytest
from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MoneyBacking, MoneyForm
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import FactionStats, ResourceStats
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.economy.stocks import goods_of
from aerona.engine.lore.control import set_technique
from aerona.engine.phases.society_economy import default_society, save_society
from aerona.engine.phases.trade import barter_and_rivalry, currency, impose_trade, order_minting, trade_income
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, bonded, chronicle_keys, context, knowledge, link, make, people, settlement, trade_route, tuned


async def society(realm: Realm, entity: EntityRow) -> CommunitySocietyRow:
    return await save_society(realm.session, entity.id, default_society(Rules()))


async def test_routes_bring_prosperity_and_wealth(realm: Realm) -> None:
    first = await people(realm, "Ama", prosperity=30, wealth=30)
    second = await people(realm, "Bel", prosperity=30, wealth=30)
    await trade_route(realm, first, second)
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


async def test_a_scarce_community_seizes_a_weaker_neighbours_ore(realm: Realm) -> None:
    hungry = await settlement(realm, "Eastwell")
    holder = await settlement(realm, "Westwell")
    await link(realm.session, hungry.id, (await knowledge(realm, "Spearcraft", KnowledgeBranch.WARFARE)).id, BondKind.KNOWS)
    hill = await make(realm.session, "Iron Hill", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=realm.world.id, location_id=realm.region.id)
    await set_resource_yield(realm.session, Rules(), hill.id, CommodityKind.ORE, MaterialKind.IRON)
    await link(realm.session, holder.id, hill.id, BondKind.OWNS)
    ctx = context(realm.session, tuned(trade={"rivalry_war_chance": 100}))
    await barter_and_rivalry(ctx)
    assert await bonded(realm.session, hungry.id, holder.id, BondKind.ENEMY)
    assert "trade.seize_resource" in await chronicle_keys(realm.session)


async def test_minting_adoption_and_shared_coin(realm: Realm) -> None:
    minter = await settlement(realm, "Mint", prosperity=90)
    partner = await settlement(realm, "Buyer", prosperity=40)
    await society(realm, minter)
    await society(realm, partner)
    trading = await knowledge(realm, "Coinage", KnowledgeBranch.TRADE)
    await link(realm.session, minter.id, trading.id, BondKind.KNOWS)
    await link(realm.session, minter.id, partner.id, BondKind.TRADES_WITH)
    await goods_of(realm.session, 1).add(minter.id, CommodityKind.ORE, 40, GoodsFlow.PLAYER, material=MaterialKind.SILVER)
    ctx = context(realm.session, tuned(trade={"coinage_chance": 100, "currency_adopt_chance": 100}))
    await currency(ctx)
    coin = await realm.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == minter.id))
    assert coin is not None and coin.metal is MaterialKind.SILVER and coin.supply > 0
    item = await realm.session.get(EntityRow, coin.item_entity_id)
    assert item is not None and item.engine_kind is EngineKind.CURRENCY
    adopter = await realm.session.get(CommunitySocietyRow, partner.id)
    assert adopter is not None and adopter.currency_id == coin.id
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
    item = await realm.session.get(EntityRow, coin.item_entity_id)
    assert coin.metal is MaterialKind.COPPER and item is not None and item.engine_kind is EngineKind.CURRENCY
    with pytest.raises(ValidationFailedError):
        await order_minting(ctx, guild.id)


async def test_a_town_without_coin_metal_issues_the_money_its_age_knows(realm: Realm) -> None:
    issuer = await settlement(realm, "Ledgerford", prosperity=90)
    await society(realm, issuer)
    trading = await knowledge(realm, "Reckoning", KnowledgeBranch.TRADE)
    await link(realm.session, issuer.id, trading.id, BondKind.KNOWS)
    plain = await settlement(realm, "Plainfold", prosperity=90)
    await society(realm, plain)
    await link(realm.session, plain.id, trading.id, BondKind.KNOWS)
    ctx = context(realm.session, tuned(trade={"coinage_chance": 100}))
    for technique in (Technique.COINAGE, Technique.PRINTING, Technique.DOUBLE_ENTRY):
        await set_technique(ctx, issuer.id, technique, held=True, secret=False)
    await currency(ctx)
    money = await realm.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == issuer.id))
    assert money is not None and money.form is MoneyForm.LEDGER and money.metal is None and money.backing is MoneyBacking.DECREE
    assert "money.issued" in await chronicle_keys(realm.session)
    assert await realm.session.scalar(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == plain.id)) is None
