from sqlalchemy import select

from aerona.db.tables.culture import BookContentRow, ItemProfileRow
from aerona.db.tables.economy import CommunityStockRow, LoanRow, MarketPriceRow, ProductionRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.finance import CreditProfileRow, EconomicIndicatorRow, TradePolicyRow
from aerona.db.tables.mind import FacetRow
from aerona.db.tables.polity import LawJurisdictionRow, LawProfileRow, PolityMemberRow, PolityProfileRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import Facet
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, Jurisdiction, LawArea, LawKind, TreatyKind, TreatyStatus
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import FactionStats, ItemStats, KnowledgeStats, LawStats, PolityStats, TreatyStats
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.markets import elasticity_of, income_of
from aerona.engine.economy.stocks import goods_of
from aerona.engine.finance.access import access_pct, sold_share
from aerona.engine.finance.contraband import smuggle_books, traffic
from aerona.engine.finance.credit import CreditTally, interest_for, on_default, rate, rated_interest
from aerona.engine.finance.indicators import IndicatorTally, record_indicators
from aerona.engine.finance.policy import PolicyBook, PolicyTally, smuggle, tend_policies
from aerona.engine.finance.speculation import SpeculationTally, open_hoard, settle_hoards
from aerona.engine.industry.energy import industry_row
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned

RULES = Rules()


async def realm_of(realm: Realm, name: str, *members: EntityRow) -> EntityRow:
    polity = await make(realm.session, name, EntityType.POLITY, PolityStats(stability=60), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(polity_entity_id=polity.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, treasury=200, locked=[])
    )
    for member in members:
        realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=member.id, locked=[]))
    await realm.session.flush()
    return polity


async def test_access_elasticity_and_income_follow_roads_routes_goods_and_prosperity(realm: Realm) -> None:
    ctx = context(realm.session)
    assert access_pct(RULES, 0, []) == RULES.market_access.base_pct
    assert access_pct(RULES, 3, [(10, 0), (10, 0)]) > access_pct(RULES, 3, [(90, 0), (90, 0)]) > access_pct(RULES, 0, [])
    assert sold_share(RULES, None) == 1.0
    assert elasticity_of(ctx, CommodityKind.GRAIN) < elasticity_of(ctx, CommodityKind.TOOLS) < elasticity_of(ctx, CommodityKind.LUXURIES)
    rich = await settlement(realm, "Goldmere", prosperity=90)
    poor = await settlement(realm, "Ashfall", prosperity=10)
    assert income_of(ctx, rich, CommodityKind.LUXURIES) > 1.0 > income_of(ctx, poor, CommodityKind.LUXURIES)
    assert income_of(ctx, rich, CommodityKind.GRAIN) == 1.0


async def test_tariffs_embargoes_and_bans_set_terms_and_smugglers_run_them(realm: Realm) -> None:
    ctx = context(realm.session)
    home, abroad = await settlement(realm, "Portsmere"), await settlement(realm, "Farhold")
    crown, rival = await realm_of(realm, "Crownlands", home), await realm_of(realm, "Rivalreach", abroad)
    realm.session.add(
        TradePolicyRow(issuer_node_id=crown.id, kind=TradePolicyKind.TARIFF, commodity=CommodityKind.TOOLS, rate_pct=25, since_epoch=1, locked=[])
    )
    realm.session.add(
        TradePolicyRow(issuer_node_id=crown.id, kind=TradePolicyKind.EMBARGO, partner_node_id=rival.id, commodity=CommodityKind.ORE, since_epoch=1, locked=[])
    )
    gang = await make(realm.session, "Black Sails", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=gang.id, kind=FactionKind.PIRATES, home_entity_id=home.id, treasury=0))
    realm.session.add(SettlementProfileRow(settlement_entity_id=home.id, size_tier=SizeTier.TOWN, crime=10))
    realm.session.add(CommunityStockRow(community_entity_id=abroad.id, commodity=CommodityKind.ORE, quantity=100, quality=50))
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    policies = await PolicyBook.load(ctx, book)
    tools = policies.terms(abroad.id, home.id, CommodityKind.TOOLS)
    assert tools.tariff_pct == 25 and not tools.blocked and tools.buyer_realm == crown.id
    assert policies.terms(abroad.id, home.id, CommodityKind.ORE).embargo
    assert policies.terms(home.id, home.id, CommodityKind.TOOLS).tariff_pct == 0
    tally = PolicyTally()
    moved = await smuggle(ctx, book, policies, seller=abroad.id, buyer=home.id, commodity=CommodityKind.ORE, volume=60, landed=100.0, tally=tally)
    assert moved > 0 and tally.smuggled == moved
    gang_profile = await realm.session.get(FactionProfileRow, gang.id)
    town = await realm.session.get(SettlementProfileRow, home.id)
    assert gang_profile is not None and gang_profile.treasury > 0 and town is not None and town.crime > 10
    assert industry_row(ctx, book, home.id).black_market == moved


async def test_credit_rates_borrowers_and_a_default_brings_restructuring(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Debtford")
    crown = await realm_of(realm, "Owing Crown", town)
    bank = await make(realm.session, "Silver House", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=bank.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=town.id, treasury=500))
    realm.session.add(
        LoanRow(
            lender_entity_id=bank.id,
            borrower_entity_id=crown.id,
            principal=100,
            interest_pct=10,
            issued_epoch=1,
            due_epoch=5,
            status=LoanStatus.REPAID,
            purpose="war",
        )
    )
    await realm.session.flush()
    tally = CreditTally()
    row = await rate(ctx, crown.id, tally)
    assert row is not None and row.state is CreditState.NORMAL and row.rating > 50 and tally.rated == 1
    assert await interest_for(ctx, crown.id, 99) == row.interest_pct
    good = row.interest_pct
    await on_default(ctx, crown, bank)
    assert row.state is CreditState.DEFAULT and row.defaults == 1 and row.restructured_until is not None
    await rate(ctx, crown.id, tally)
    assert row.state is CreditState.RESTRUCTURING and row.interest_pct > good


async def test_greedy_merchants_hoard_and_a_fall_in_price_ruins_them(realm: Realm) -> None:
    ctx = context(realm.session)
    market = await settlement(realm, "Bazaarton")
    trader = await mortal(realm, "Vesk", location_id=market.id, role=MortalRole.MERCHANT)
    realm.session.add(FacetRow(node_id=trader.id, facet=Facet.GREED, value=40))
    realm.session.add(CommunityStockRow(community_entity_id=market.id, commodity=CommodityKind.LUXURIES, quantity=200, quality=50))
    realm.session.add(
        FactionProfileRow(
            faction_entity_id=(await make(realm.session, "Coin Guild", EntityType.FACTION, FactionStats(), world_id=realm.world.id)).id,
            kind=FactionKind.MERCHANT_GUILD,
            home_entity_id=market.id,
            treasury=1000,
        )
    )
    await realm.session.flush()
    guild = await realm.session.scalar(select(FactionProfileRow).where(FactionProfileRow.home_entity_id == market.id))
    assert guild is not None
    row = await open_hoard(ctx, guild.faction_entity_id, market, CommodityKind.LUXURIES, 100, famine=False)
    assert row is not None and row.units == 40 and row.status is SpeculationStatus.HOARDING
    stock = await realm.session.scalar(select(CommunityStockRow).where(CommunityStockRow.community_entity_id == market.id))
    assert stock is not None and stock.quantity == 160
    realm.session.add(MarketPriceRow(market_entity_id=market.id, commodity=CommodityKind.LUXURIES, epoch=ctx.epoch, price=50, supply=160, demand=100))
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    tally = SpeculationTally()
    await settle_hoards(ctx, book, tally)
    assert row.status is SpeculationStatus.BUST and row.gain < 0 and tally.busts == 1 and stock.quantity == 200
    assert trader.id > 0


async def test_realms_and_worlds_keep_their_economic_indicators(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Countwell")
    crown = await realm_of(realm, "Ledger Crown", town)
    realm.session.add(
        ProductionRunRow(epoch=ctx.epoch, community_entity_id=town.id, step="mill", output=CommodityKind.BREAD, quantity=50, quality=50, inputs={}, workers=10)
    )
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    tally = IndicatorTally()
    await record_indicators(ctx, book, tally)
    rows = list(await realm.session.scalars(select(EconomicIndicatorRow).where(EconomicIndicatorRow.epoch == ctx.epoch)))
    subjects = {row.subject_node_id for row in rows}
    assert crown.id in subjects and realm.world.id in subjects and tally.recorded == len(rows)
    mine = next(row for row in rows if row.subject_node_id == crown.id)
    assert mine.output > 0 and mine.treasury == 200 and await realm.session.get(CreditProfileRow, crown.id) is None


async def test_capacity_widens_access_allies_join_embargoes_and_thin_coin_raises_interest(realm: Realm) -> None:
    ctx = context(realm.session)
    assert access_pct(RULES, 0, [(0, 100)]) > access_pct(RULES, 0, [(0, 0)])
    assert rated_interest(ctx, 60, 80) > rated_interest(ctx, 60, 0)
    one, two, foe = await settlement(realm, "Allyton"), await settlement(realm, "Pactmere"), await settlement(realm, "Foehold")
    first, second, enemy = await realm_of(realm, "First Crown", one), await realm_of(realm, "Second Crown", two), await realm_of(realm, "Foe Crown", foe)
    pact = await make(realm.session, "The Iron Pact", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    realm.session.add(TreatyProfileRow(treaty_entity_id=pact.id, kind=TreatyKind.ALLIANCE_DEFENSIVE, status=TreatyStatus.IN_FORCE, signed_epoch=1))
    realm.session.add_all([TreatyPartyRow(treaty_entity_id=pact.id, party_node_id=first.id), TreatyPartyRow(treaty_entity_id=pact.id, party_node_id=second.id)])
    realm.session.add(
        TradePolicyRow(issuer_node_id=first.id, kind=TradePolicyKind.EMBARGO, partner_node_id=enemy.id, rate_pct=100, since_epoch=1, locked=["kind"])
    )
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    policies = await PolicyBook.load(ctx, book)
    rules = tuned(trade_policy={"treaty_embargo_chance": 100})
    await tend_policies(context(realm.session, rules), book, policies, PolicyTally())
    joined = await realm.session.scalar(select(TradePolicyRow).where(TradePolicyRow.issuer_node_id == second.id, TradePolicyRow.partner_node_id == enemy.id))
    assert joined is not None and joined.kind is TradePolicyKind.EMBARGO and "treaty" in (joined.reason or "")


async def law(realm: Realm, name: str, kind: LawKind, place: EntityRow, **params: str) -> None:
    entity = await make(realm.session, name, EntityType.LAW, LawStats(), world_id=realm.world.id)
    realm.session.add(LawProfileRow(law_entity_id=entity.id, kind=kind, area=LawArea.PENAL, params=params, enforcement=80))
    realm.session.add(LawJurisdictionRow(law_entity_id=entity.id, node_entity_id=place.id, jurisdiction=Jurisdiction.POLITY))
    await realm.session.flush()


async def test_bans_on_magic_forbid_void_materials_and_outlaws_traffic_captives_and_books(realm: Realm) -> None:
    ctx = context(realm.session, tuned(contraband={"slave_chance": 100}))
    free, bound = await settlement(realm, "Freeholm"), await settlement(realm, "Chainport")
    gang = await make(realm.session, "Red Hands", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=gang.id, kind=FactionKind.BANDITS, home_entity_id=free.id, treasury=0))
    realm.session.add(SettlementProfileRow(settlement_entity_id=free.id, size_tier=SizeTier.TOWN, crime=10))
    await law(realm, "Law of the Bound", LawKind.SLAVERY, bound, status="allowed")
    await law(realm, "Ban on Sorcery", LawKind.MAGIC_BAN, free)
    realm.session.add(CommunityStockRow(community_entity_id=bound.id, commodity=CommodityKind.ORE, material=MaterialKind.VOID_GLASS, quantity=20, quality=50))
    realm.session.add(CommunityStockRow(community_entity_id=bound.id, commodity=CommodityKind.ORE, material=MaterialKind.IRON, quantity=20, quality=50))
    lore = await make(
        realm.session, "Unspoken Names", EntityType.KNOWLEDGE, KnowledgeStats(), world_id=realm.world.id, knowledge_branch=KnowledgeBranch.FORBIDDEN
    )
    tome = await make(realm.session, "The Grey Codex", EntityType.ITEM, ItemStats(), world_id=realm.world.id, location_id=free.id)
    realm.session.add(ItemProfileRow(item_entity_id=tome.id, item_class=ItemClass.BOOK))
    realm.session.add(BookContentRow(book_entity_id=tome.id, knowledge_entity_id=lore.id))
    await realm.session.flush()
    market = await traffic(ctx, free, 40, None)
    profile = await realm.session.get(FactionProfileRow, gang.id)
    town = await realm.session.get(SettlementProfileRow, free.id)
    assert market is not None and market.id == bound.id and profile is not None and profile.treasury > 0 and town is not None and town.crime > 10
    book = await EconomyBook.load(ctx)
    policies = await PolicyBook.load(ctx, book)
    banned = policies.banned.get(free.id)
    assert banned is not None and MaterialKind.VOID_GLASS in banned.kinds and policies.banned.get(bound.id) is None
    lawful = await goods_of(realm.session, ctx.epoch).take(bound.id, CommodityKind.ORE, 40, GoodsFlow.TRADE, exclude=banned.kinds)
    assert {lot.material for lot in lawful} == {MaterialKind.IRON}
    before = profile.treasury
    assert await smuggle_books(ctx, profile) == 1 and profile.treasury > before
