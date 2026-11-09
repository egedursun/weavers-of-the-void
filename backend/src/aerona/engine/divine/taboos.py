from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import CreatorTabooRow
from aerona.domain.enums.mind import ActKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_percent


async def taboo_broken(ctx: TickContext, actor_id: int, act: ActKind) -> bool:
    row = await ctx.session.get(CreatorTabooRow, act)
    if row is None:
        return False
    creator = await ctx.session.scalar(select(CreatorRow).limit(1))
    row.broken += 1
    row.last_broken_epoch, row.last_breaker_node_id = ctx.epoch, actor_id
    if creator is not None:
        creator.mood_anger = clamp_percent(creator.mood_anger + row.severity * ctx.rules.creator.taboo_anger_pct / PERCENT)
    return True
