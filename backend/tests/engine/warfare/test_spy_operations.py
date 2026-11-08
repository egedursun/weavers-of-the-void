from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import SpyOperation
from aerona.engine.phases.espionage import OPERATIONS, incite_uprising_quietly
from aerona.engine.primitives.stats import stat
from tests.engine.warfare.factories import bond, make, make_ctx


async def network(session: AsyncSession, owner_id: int, target_id: int, intel: int) -> SpyNetworkRow:
    row = SpyNetworkRow(owner_entity_id=owner_id, target_entity_id=target_id, intel=intel, since_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    return row


async def test_a_deep_network_blackmails_and_a_shallow_one_cannot(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    spymaster = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, wealth=10)
    target = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000, wealth=50)
    shallow = await network(session, spymaster.id, target.id, 0)
    assert await OPERATIONS[SpyOperation.BLACKMAIL](ctx, spymaster, target, shallow) is None
    deep = await network(session, spymaster.id, target.id, 100)
    assert await OPERATIONS[SpyOperation.BLACKMAIL](ctx, spymaster, target, deep) is not None
    assert (stat(spymaster, "wealth") or 0) > 10 and (stat(target, "wealth") or 0) < 50 and deep.intel < 100


async def test_false_coin_saps_the_trust_in_a_rivals_money(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    spymaster = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    target = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    row = await network(session, spymaster.id, target.id, 50)
    assert await OPERATIONS[SpyOperation.COUNTERFEIT](ctx, spymaster, target, row) is None
    coin = CurrencyRow(issuer_entity_id=target.id, name="Reed mark", metal=next(iter(MaterialKind)), purity=80, supply=100, trust=60, minted_epoch=1)
    session.add(coin)
    await session.flush()
    assert await OPERATIONS[SpyOperation.COUNTERFEIT](ctx, spymaster, target, row) is not None
    assert coin.trust == 60 - ctx.rules.espionage.counterfeit_trust


async def test_a_quiet_hand_stirs_a_town_against_its_ruler(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    lord = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    town = await make(session, "Highwall", EntityType.SETTLEMENT, world_id, population=900)
    assert not await incite_uprising_quietly(ctx, town)
    await bond(session, lord.id, town.id, BondKind.RULES)
    assert await incite_uprising_quietly(ctx, town)
    enemy = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == town.id))
    assert enemy is not None and enemy.target_node_id == lord.id
