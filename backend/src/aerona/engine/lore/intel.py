from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.military import SpyNetworkRow
from aerona.domain.enums.military import SpyCover
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int

SCRYING = "scrying"


async def gain_intel(ctx: TickContext, owner_id: int, target_id: int, amount: int) -> None:
    found = await ctx.session.scalar(
        select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == owner_id, SpyNetworkRow.target_entity_id == target_id).order_by(SpyNetworkRow.id).limit(1)
    )
    if found is None:
        found = SpyNetworkRow(
            owner_entity_id=owner_id,
            target_entity_id=target_id,
            agents=0,
            agent_ids=[],
            depth=0,
            exposure=0,
            cover=SpyCover.BEGGAR,
            since_epoch=ctx.epoch,
            intel=0,
        )
        ctx.session.add(found)
    found.intel = clamp_int(found.intel + amount, 0, PERCENT)
    found.last_operation, found.last_epoch = SCRYING, ctx.epoch
