from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.war import DebtStatus
from aerona.domain.models.entity_stats import ResourceStats
from aerona.engine.economy.control import open_route
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.phases.commerce import trade_flow
from aerona.engine.phases.market import market, write_off_debt
from aerona.engine.phases.society_economy import default_society, save_society
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def test_goods_flow_from_cheap_to_dear_stores_and_poor_buyers_owe(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(market={"credit_threshold": 100})
    rich = await settlement(session, "Brennhold", world, world.regions[0], prosperity=60)
    poor = await settlement(session, "Ashwick", world, world.regions[1], prosperity=10)
    for town in (rich, poor):
        await save_society(session, town.id, default_society(rules))
    ctx = await manual_context(session, "test", rules)
    await goods_of(session, ctx.epoch).add(rich.id, CommodityKind.GRAIN, 4000, GoodsFlow.PLAYER)
    await open_route(ctx, route_id=None, first_id=rich.id, second_id=poor.id)
    await trade_flow(ctx)
    assert await holding(session, rich.id, CommodityKind.GRAIN) < 4000
    assert await holding(session, poor.id, CommodityKind.GRAIN) > 0
    debts = await BondRepository(session).active_between(poor.id, rich.id, [BondKind.OWES])
    assert debts and debts[0].debt_status is DebtStatus.OPEN


async def test_overdue_debts_lapse_and_can_be_written_off(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    lender = await settlement(session, "Velmoor", world, world.regions[0])
    debtor = await settlement(session, "Tarn", world, world.regions[1])
    bonds = BondRepository(session)
    old = await bonds.connect(BondDraft(debtor.id, lender.id, BondKind.OWES, 1, "old loan", debt_amount=5, debt_what="grain", debt_due_epoch=-20))
    old.debt_status = DebtStatus.OPEN
    await market(await manual_context(session, "test", rules))
    assert old.state is BondState.PAST
    fresh = await bonds.connect(BondDraft(debtor.id, lender.id, BondKind.OWES, 1, "new loan", debt_amount=3, debt_what="grain", debt_due_epoch=9))
    await write_off_debt(session, rules, fresh.id)
    assert fresh.state is BondState.PAST and fresh.debt_status is DebtStatus.FORGIVEN


async def test_crowded_resources_run_out(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(market={"depletion_chance": 100, "demand_population": 1000})
    seam = ResourceStats(abundance=3, value=50, might=10)
    vein = await entity(session, "Copper Seam", EntityType.RESOURCE, seam, world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, world.people.id, vein.id, BondKind.OWNS)
    await market(await manual_context(session, "first", rules))
    assert await has_flag(session, vein.id, EntityFlag.DEPLETING)
    await market(await manual_context(session, "second", rules))
    assert await has_flag(session, vein.id, EntityFlag.DEPLETED)
