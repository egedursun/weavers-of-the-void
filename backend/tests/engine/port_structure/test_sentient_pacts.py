from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.models.entity_stats import ResourceStats
from aerona.engine.economy.stocks import goods_of
from aerona.engine.gods.economy import resource_mechanics
from aerona.engine.gods.pacts import end_pact, pact_by_hand, pact_for, pact_terms
from aerona.engine.gods.queries import owners_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

PLENTY = 5000


async def sentient(session: AsyncSession, world: CoreWorld) -> tuple:
    keeper = await settlement(session, "Hollowmere", world, world.regions[0], prosperity=90)
    vein = await entity(session, "The Whispering Seam", EntityType.RESOURCE, ResourceStats(abundance=60, value=50, might=20), world_id=world.world.id)
    session.add(ResourceMechanicRow(entity_id=vein.id, mechanic=ResourceMechanic.SENTIENT, magnitude=5, epochs=None))
    await bond(session, keeper.id, vein.id, BondKind.OWNS)
    speaker = await mortal(session, "Oriel the Tongue", world, keeper.id)
    session.add(SkillRow(holder_node_id=speaker.id, skill=SkillKind.NEGOTIATION, level=10, peak=10, last_used_epoch=1, source=SkillSource.PLAYER))
    await session.flush()
    return keeper, vein


async def stock_up(session: AsyncSession, epoch: int, keeper_id: int) -> None:
    for kind in (CommodityKind.SACRED_GOODS, CommodityKind.LUXURIES, CommodityKind.GRAIN):
        await goods_of(session, epoch).add(keeper_id, kind, PLENTY, GoodsFlow.PLAYER)


async def test_a_negotiated_demand_becomes_a_pact_that_is_kept_then_broken(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(
        economy={"sentient_resource_choose_chance": 100, "sentient_resource_keep_chance": 0, "sentient_bargain_pct_per_level": 100},
        sentient_pacts={"every_epochs": 1},
    )
    keeper, vein = await sentient(session, world)
    ctx = await manual_context(session, "test", rules)
    await stock_up(session, ctx.epoch, keeper.id)
    await resource_mechanics(ctx)
    pact = await pact_for(session, vein.id)
    assert pact is not None
    profile, clause = pact
    assert clause.kind is ClauseKind.RESOURCE_DEMAND and clause.obligor_node_id == keeper.id and clause.beneficiary_node_id == vein.id
    assert clause.params["paid_epoch"] == ctx.epoch and clause.last_kept_epoch == ctx.epoch
    world.cosmos.epoch += 1
    for kind in (CommodityKind.SACRED_GOODS, CommodityKind.LUXURIES, CommodityKind.GRAIN):
        await goods_of(session, world.cosmos.epoch).take_units(keeper.id, kind, PLENTY, GoodsFlow.PLAYER)
    set_stats(keeper, prosperity=0)
    await session.flush()
    later = await manual_context(session, "later", rules)
    await resource_mechanics(later)
    assert profile.status is TreatyStatus.BROKEN
    assert keeper.id not in {owner.id for owner in await owners_of(session, vein.id)}
    assert (stat(keeper, "prosperity") or 0) == 0


async def test_the_player_strikes_edits_and_releases_a_pact(session: AsyncSession, world: CoreWorld) -> None:
    keeper, vein = await sentient(session, world)
    ctx = await manual_context(session, "test", tuned_rules())
    treaty = await pact_by_hand(ctx, vein.id, keeper.id, {"demand": "a song each dawn", "commodity": "luxuries", "units": 9, "every": 3}, epochs=5)
    clause = await session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty.id))
    assert clause is not None and clause.params["units"] == 9 and clause.params["commodity"] == "luxuries"
    await pact_terms(ctx, treaty.id, {"units": 3, "commodity": ""})
    assert clause.params["units"] == 3 and clause.params["commodity"] == ""
    profile = await end_pact(ctx, treaty.id)
    assert profile.status is TreatyStatus.FULFILLED
    assert await session.get(TreatyProfileRow, treaty.id) is not None
