from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.economy import stores_for
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.demography import CohortRow, LabourRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.economy import CurrencyRow, LoanRow, MarketPriceRow, TradeRouteLossRow, TradeRouteProfileRow, TradeRouteTollRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job, Sex
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus, TradeLoss
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import DebtStatus
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.economy.control import open_route
from aerona.engine.economy.stocks import goods_of
from aerona.engine.phases.society_economy import default_society, save_society
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.tools.framework.views import entity_detail
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement

LOT_MATERIALS = (MaterialKind.IRON, MaterialKind.COPPER, MaterialKind.TIN, MaterialKind.SILVER, MaterialKind.GOLD, MaterialKind.LEAD, MaterialKind.STONE)


async def test_inspection_and_mortal_context_carry_the_whole_economy(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    town = await settlement(session, "Coppermouth", world, world.regions[0])
    other = await settlement(session, "Tinhollow", world, world.regions[2])
    for item in (town, other):
        await save_society(session, item.id, default_society(rules), stocks=False)
    ctx = await manual_context(session, "test", rules)
    for index, material in enumerate(LOT_MATERIALS):
        await goods_of(session, ctx.epoch).add(town.id, CommodityKind.ORE, 10 + index, GoodsFlow.PLAYER, material=material, quality=40 + index)
    await goods_of(session, ctx.epoch).add(town.id, CommodityKind.GRAIN, 300, GoodsFlow.PLAYER, quality=55)
    session.add(MarketPriceRow(market_entity_id=town.id, commodity=CommodityKind.GRAIN, epoch=ctx.epoch, price=135, supply=300, demand=420))
    coin = CurrencyRow(issuer_entity_id=town.id, name="Copper Mark", metal=MaterialKind.COPPER, purity=81, supply=900, trust=64, minted_epoch=1)
    session.add(coin)
    await session.flush()
    society = await session.get(CommunitySocietyRow, town.id)
    assert society is not None
    society.currency_id = coin.id
    session.add(
        LoanRow(
            lender_entity_id=other.id,
            borrower_entity_id=town.id,
            principal=20,
            interest_pct=10,
            issued_epoch=1,
            due_epoch=5,
            status=LoanStatus.OPEN,
            purpose="war",
        )
    )
    owed = await BondRepository(session).connect(
        BondDraft(town.id, other.id, BondKind.OWES, 1, "grain debt", debt_amount=40, debt_what="grain", debt_due_epoch=6)
    )
    owed.debt_status = DebtStatus.OPEN
    road = await open_route(ctx, route_id=None, first_id=town.id, second_id=other.id)
    profile = await session.get(TradeRouteProfileRow, road.id)
    assert profile is not None
    profile.danger_beasts, profile.danger_weather, profile.season_pct, profile.chokepoint = 22, 13, 70, True
    session.add(TradeRouteTollRow(route_entity_id=road.id, region_entity_id=world.regions[1].id, controller_entity_id=other.id, rate_pct=8))
    session.add(TradeRouteLossRow(route_entity_id=road.id, epoch=ctx.epoch, commodity=CommodityKind.GRAIN, cause=TradeLoss.WEATHER, units=17))
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=120, locked=[], foreigners={}))
    session.add(DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.MARKET, level=2, built_epoch=1))
    session.add(
        CohortRow(
            community_entity_id=town.id, age_band=AgeBand.ADULT, sex=Sex.FEMALE, social_class=SocialClass.FARMER, condition=CohortCondition.SICK, count=310
        )
    )
    session.add(LabourRow(community_entity_id=town.id, job=Job.FARMING, workers=800, output_pct=90))
    plague = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(virulence=40), world_id=world.world.id)
    session.add(
        OutbreakRow(
            disease_entity_id=plague.id,
            region_entity_id=world.regions[0].id,
            path=SpreadPath.ROUTE,
            status=OutbreakStatus.ACTIVE,
            severity=44,
            infected=90,
            dead=5,
            started_epoch=1,
        )
    )
    session.add(EndemicDiseaseRow(region_entity_id=world.regions[0].id, disease_entity_id=plague.id, load=30, since_epoch=1))
    await session.flush()
    text = await entity_detail(session, rules, town)
    for material in LOT_MATERIALS:
        assert material.value.replace("_", " ") in text.lower()
    for fragment in (
        "price 135, supply 300, need 420",
        "quality 55",
        "Copper Mark",
        "purity 81, trust 64",
        "borrowed from Tinhollow",
        "owes Tinhollow 40 grain",
        "beasts 22, weather 13",
        "keeps 70%",
        "a chokepoint",
        "17 grain to weather",
        "8% to Tinhollow",
        "a town; treasury 120",
        "market level 2",
        "310 adult female farmer (sick)",
        "farming 800 hands at 90%",
        "Grey Cough",
        "load 30",
    ):
        assert fragment in text, fragment
    route_text = await entity_detail(session, rules, road)
    assert "beasts 22" in route_text and "17 grain to weather" in route_text
    worker = await mortal(session, "Ilse Furrow", world, town.id)
    worker.social_class = SocialClass.FARMER
    await BondRepository(session).connect(BondDraft(worker.id, town.id, BondKind.MEMBER_OF, 1, "home"))
    stores = await stores_for(session, rules, worker)
    assert stores is not None
    assert len(stores.materials) == 2 and all(material.value.replace("_", " ") in stores.materials[1].lower() for material in LOT_MATERIALS)
    assert any("grain 135" in price for price in stores.prices)
    assert "Copper Mark" in stores.currency
    assert any("Tinhollow" in debt for debt in stores.debts) and stores.loans
    assert "farming" in stores.job and "800 hands" in stores.job
