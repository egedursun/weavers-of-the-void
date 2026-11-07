import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.finance import CreditProfileRow, EconomicIndicatorRow, SpeculationRow, TradePolicyRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.services.player import finance
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_lays_and_lifts_tariffs_and_embargoes(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    crown = await make_entity(session, "Crown", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    rival = await make_entity(session, "Rival", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    made = await finance.set_trade_policy(
        scope, finance.SetTradePolicy(issuer_id=crown.id, kind=TradePolicyKind.TARIFF, commodity=CommodityKind.TOOLS, rate_pct=30)
    )
    row = await session.get(TradePolicyRow, made.values["policy_id"])
    assert row is not None and row.rate_pct == 30 and set(row.locked) == {"rate_pct", "kind"}
    again = await finance.set_trade_policy(
        scope, finance.SetTradePolicy(issuer_id=crown.id, kind=TradePolicyKind.TARIFF, commodity=CommodityKind.TOOLS, rate_pct=10)
    )
    assert again.values["policy_id"] == row.id and row.rate_pct == 10
    with pytest.raises(ValidationFailedError):
        await finance.set_trade_policy(scope, finance.SetTradePolicy(issuer_id=crown.id, kind=TradePolicyKind.EMBARGO))
    embargo = await finance.set_trade_policy(scope, finance.SetTradePolicy(issuer_id=crown.id, kind=TradePolicyKind.EMBARGO, partner_id=rival.id))
    stopped = await session.get(TradePolicyRow, embargo.values["policy_id"])
    assert stopped is not None and stopped.rate_pct == 100
    await finance.remove_trade_policy(scope, finance.TradePolicyTarget(policy_id=row.id))
    assert await session.get(TradePolicyRow, row.id) is None


async def test_the_god_sets_and_wipes_credit(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    crown = await make_entity(session, "Ledgerholm", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await finance.set_credit(scope, finance.SetCredit(subject_id=crown.id, rating=20, state=CreditState.STRAINED, reserves=300))
    row = await session.get(CreditProfileRow, crown.id)
    assert row is not None and row.rating == 20 and row.state is CreditState.STRAINED and set(row.locked) == {"rating", "state", "reserves"}
    with pytest.raises(ValidationFailedError):
        await finance.set_credit(scope, finance.SetCredit(subject_id=crown.id))
    await finance.remove_credit(scope, finance.CreditTarget(subject_id=crown.id))
    assert await session.get(CreditProfileRow, crown.id) is None


async def test_the_god_hoards_retells_and_strikes_a_hoard(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Marketon", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    trader = await make_entity(session, "Ivo", EntityType.MORTAL, world_id=world.world.id, location_id=city.id)
    lot = CommunityStockRow(community_entity_id=city.id, commodity=CommodityKind.GRAIN, quantity=100, quality=50)
    session.add(lot)
    await session.flush()
    made = await finance.open_speculation(
        scope, finance.OpenSpeculation(merchant_id=trader.id, market_id=city.id, commodity=CommodityKind.GRAIN, units=30, price=12)
    )
    row = await session.get(SpeculationRow, made.values["speculation_id"])
    assert row is not None and row.units == 30 and lot.quantity == 70
    await finance.edit_speculation(scope, finance.EditSpeculation(speculation_id=row.id, status=SpeculationStatus.SOLD, gain=40))
    assert row.status is SpeculationStatus.SOLD and row.gain == 40 and row.settled_epoch is not None
    await finance.edit_speculation(scope, finance.EditSpeculation(speculation_id=row.id, status=SpeculationStatus.HOARDING))
    await finance.remove_speculation(scope, finance.SpeculationTarget(speculation_id=row.id))
    assert await session.get(SpeculationRow, row.id) is None and lot.quantity == 100


async def test_the_god_rewrites_and_strikes_a_record_of_the_economy(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    entry = EconomicIndicatorRow(subject_node_id=world.world.id, epoch=2, output=10, living={}, locked=[])
    session.add(entry)
    await session.flush()
    await finance.edit_indicator(scope, finance.EditIndicator(indicator_id=entry.id, output=99, trade_balance=-5))
    assert entry.output == 99 and entry.trade_balance == -5 and set(entry.locked) == {"output", "trade_balance"}
    await finance.remove_indicator(scope, finance.IndicatorTarget(indicator_id=entry.id))
    assert await session.get(EconomicIndicatorRow, entry.id) is None
    with pytest.raises(NotFoundError):
        await finance.remove_indicator(scope, finance.IndicatorTarget(indicator_id=entry.id))
