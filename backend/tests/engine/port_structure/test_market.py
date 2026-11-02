from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import DebtStatus
from aerona.domain.models.entity_stats import ResourceStats
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
    cheap, dear = default_society(rules), default_society(rules)
    cheap.stocks[Commodity.FOOD], cheap.prices[Commodity.FOOD] = 400, 50
    dear.stocks[Commodity.FOOD], dear.prices[Commodity.FOOD] = 10, 200
    await save_society(session, rich.id, cheap)
    await save_society(session, poor.id, dear)
    await bond(session, rich.id, poor.id, BondKind.TRADES_WITH)
    await market(await manual_context(session, "test", rules))
    seller, buyer = await session.get(CommunitySocietyRow, rich.id), await session.get(CommunitySocietyRow, poor.id)
    assert seller is not None and buyer is not None
    assert seller.stock(Commodity.FOOD) < 400 < buyer.stock(Commodity.FOOD) + 400
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
