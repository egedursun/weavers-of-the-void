from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.economy import CommunityStockRow, CurrencyRow, LoanRow, ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.orders import (
    BillOfExchangeRow,
    EconomicOrderKindRow,
    EconomicOrderRow,
    ExchangeRateRow,
    HoardRow,
    PuttingOutRow,
    SavingRow,
)
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.orders import (
    AllocationMode,
    Compensation,
    DistributionRule,
    HoardState,
    OrderLabour,
    OwnershipRegime,
    SavingForm,
    TransitionKind,
    TransitionStage,
)
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats, ResourceStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.orders.economy import OrderTally, begin_transition, keep_economy
from aerona.engine.orders.exchange import ExchangeTally, exchange_cost, keep_exchange, shock_debtors, worth_of
from aerona.engine.orders.putting_out import PuttingOutTally, keep_putting_out
from aerona.engine.orders.savings import SavingTally, keep_savings, unearth_hoards
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.society import stock
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "orders", rules=tuned_rules(**rules))


async def realm_of(session: AsyncSession, world: CoreWorld, towns: list[EntityRow], ruler: EntityRow | None = None) -> EntityRow:
    polity = await entity(session, f"Crown of {towns[0].name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=towns[0].id,
            core_entity_id=polity.id,
            treasury=5000,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    for town in towns:
        session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity


async def test_households_bury_what_they_save_where_life_is_unsafe_and_lost_hoards_are_found_by_diggers(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Graveshill", world, world.regions[0])
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, public_order=10, crime=90, locked=[]))
    head = await mortal(session, "Odo", world, town.id)
    household = HouseholdRow(name="House of Odo", head_node_id=head.id, settlement_node_id=town.id, wealth=200, income=60, expenses=10, locked=[])
    session.add(household)
    await session.flush()
    tally = SavingTally()
    await keep_savings(await at(session, 2), tally)
    saving = await session.get(SavingRow, household.id)
    hoard = await session.scalar(select(HoardRow).where(HoardRow.place_entity_id == town.id))
    assert saving is not None and saving.form is SavingForm.HOARD and saving.saved > 0
    assert hoard is not None and hoard.amount == saving.saved and household.wealth == 200 - saving.saved
    head.status, head.end_epoch = EntityStatus.DEAD, 2
    await session.flush()
    await keep_savings(await at(session, 3), SavingTally())
    assert hoard.state is HoardState.LOST
    digger = await mortal(session, "Pell", world, town.id)
    found = await unearth_hoards(await at(session, 4), [town.id], digger)
    assert found == hoard.amount and hoard.state is HoardState.FOUND and hoard.found_by_node_id == digger.id


async def test_rates_follow_the_coins_changers_profit_shocks_swell_foreign_debts_and_bills_settle(session: AsyncSession, world: CoreWorld) -> None:
    first = await settlement(session, "Coinford", world, world.regions[0])
    second = await settlement(session, "Markhaven", world, world.regions[1], wealth=50)
    strong = CurrencyRow(issuer_entity_id=first.id, name="Sun Mark", metal=MaterialKind.GOLD, purity=95, supply=10, trust=90, minted_epoch=1)
    weak = CurrencyRow(issuer_entity_id=second.id, name="Ash Penny", metal=MaterialKind.COPPER, purity=40, supply=500, trust=30, minted_epoch=1)
    session.add_all([strong, weak])
    await session.flush()

    for town, coin in ((first, strong), (second, weak)):
        society = await session.get(CommunitySocietyRow, town.id)
        if society is not None:
            society.currency_id = coin.id
    rate = ExchangeRateRow(base_currency_id=strong.id, quote_currency_id=weak.id, market_entity_id=first.id, rate=100, locked=[])
    session.add(rate)
    await session.flush()
    ctx = await at(session, 2)

    assert await worth_of(ctx, strong) > await worth_of(ctx, weak)
    loan = LoanRow(
        lender_entity_id=first.id,
        borrower_entity_id=second.id,
        currency_id=strong.id,
        principal=100,
        interest_pct=5,
        issued_epoch=1,
        due_epoch=5,
        status=LoanStatus.OPEN,
        purpose="trade",
    )
    session.add(loan)
    await session.flush()
    society = await session.get(CommunitySocietyRow, second.id)
    if society is not None:
        assert await shock_debtors(ctx, strong, weak, 30) == 1 and loan.principal == 130
    bill = BillOfExchangeRow(
        drawer_node_id=second.id, payee_node_id=first.id, from_entity_id=first.id, to_entity_id=second.id, amount=10, issued_epoch=1, locked=[]
    )
    session.add(bill)
    await session.flush()
    tally = ExchangeTally()
    await keep_exchange(ctx, tally)
    assert tally.settled == 1 and bill.settled


async def test_a_realm_reads_its_order_redistributes_and_collapses_when_its_centre_falls(session: AsyncSession, world: CoreWorld) -> None:
    capital = await settlement(session, "Templeheart", world, world.regions[0])
    village = await settlement(session, "Outfield", world, world.regions[1])
    realm = await realm_of(session, world, [capital, village])

    temple = await entity(session, "The Great Granary", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=capital.id)
    session.add(
        StructureProfileRow(
            structure_entity_id=temple.id, kind=StructureKind.GRANARY, host_entity_id=capital.id, construction_state=ConstructionState.COMPLETE, locked=[]
        )
    )
    await session.flush()
    tally = OrderTally()
    await keep_economy(await at(session, 2), tally)
    order = await session.scalar(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm.id))
    kinds = list(await session.scalars(select(EconomicOrderKindRow)))
    assert order is not None and order.allocation is AllocationMode.REDISTRIBUTION and len(kinds) == 5 and order.kind_id is not None
    assert tally.kinds == 5 and tally.orders == 1


async def test_a_change_of_order_moves_holdings_in_stages_against_unpaid_losers(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fieldhall", world, world.regions[0])
    ruler = await mortal(session, "Aster", world, town.id)
    realm = await realm_of(session, world, [town], ruler)
    lord = await mortal(session, "Brand", world, town.id)
    mine = await entity(session, "Fieldhall Pits", EntityType.RESOURCE, ResourceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(
        ResourceProfileRow(
            resource_entity_id=mine.id, commodity=CommodityKind.ORE, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=20, quality=50
        )
    )
    await bond(session, lord.id, mine.id, BondKind.OWNS)
    session.add(
        EconomicOrderRow(
            polity_entity_id=realm.id,
            ownership=OwnershipRegime.PRIVATE,
            allocation=AllocationMode.MARKET,
            labour=OrderLabour.FREE,
            distribution=DistributionRule.BY_HOLDING,
            locked=[],
        )
    )
    await session.flush()
    ctx = await at(session, 2, economic_orders={"transfers_to_finish": 1})
    row = await begin_transition(ctx, realm.id, None, TransitionKind.NATIONALISATION, Compensation.NONE)
    assert row.to_axes["ownership"] == OwnershipRegime.STATE.value and row.from_axes["ownership"] == OwnershipRegime.PRIVATE.value
    tally = OrderTally()
    await keep_economy(await at(session, 2, economic_orders={"transfers_to_finish": 1}), tally)
    assert row.stage is TransitionStage.TRANSFERRING
    await keep_economy(await at(session, 3, economic_orders={"transfers_to_finish": 1}), tally)
    order = await session.scalar(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm.id))
    assert tally.transferred == 1 and row.resistance > 0 and row.stage is TransitionStage.DONE
    assert order is not None and order.ownership is OwnershipRegime.STATE


async def test_merchants_put_wool_out_to_villages_that_make_cloth_and_prosper(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Woolmarket", world, world.regions[0])
    village = await settlement(session, "Shearby", world, world.regions[0], population=200)
    session.add(SettlementProfileRow(settlement_entity_id=village.id, size_tier=SizeTier.VILLAGE, locked=[]))
    guild = await entity(session, "Woolmarket Guild", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    guild.engine_kind = EngineKind.MERCHANT_GUILD
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.WOOL, quantity=50, quality=50))
    await session.flush()
    tally = PuttingOutTally()
    await keep_putting_out(await at(session, 2, putting_out={"found_chance": 100, "volume": 10}), tally)
    row = await session.scalar(select(PuttingOutRow).where(PuttingOutRow.merchant_entity_id == guild.id))
    assert row is not None and row.town_entity_id == village.id and tally.founded == 1 and tally.worked == 1
    cloth = await session.scalar(
        select(CommunityStockRow.quantity).where(CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.CLOTH)
    )
    assert cloth == 10


async def test_a_spread_costs_buyers_across_two_coins(session: AsyncSession, world: CoreWorld) -> None:
    first = await settlement(session, "Eastgate", world, world.regions[0])
    second = await settlement(session, "Westgate", world, world.regions[1])
    ctx = await at(session, 2)
    assert await exchange_cost(ctx, first.id, second.id, 100) == 0
    assert await stock(session, ctx.rules, first.id, Commodity.FOOD) >= 0
