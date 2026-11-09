from sqlalchemy import select

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.divine import CouncilRulingRow
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import CouncilMotion, SonPunishment
from aerona.engine.context import TickContext

M = CouncilMotion


async def active_rulings(ctx: TickContext, motion: CouncilMotion | None = None) -> list[CouncilRulingRow]:
    statement = select(CouncilRulingRow).where(CouncilRulingRow.active.is_(True))
    if motion is not None:
        statement = statement.where(CouncilRulingRow.motion == motion)
    return list(await ctx.session.scalars(statement.order_by(CouncilRulingRow.id)))


async def truce_in_force(ctx: TickContext) -> bool:
    return bool(await active_rulings(ctx, M.COSMIC_TRUCE))


async def outlawed_schools(ctx: TickContext) -> set[MagicSchool]:
    return {row.school for row in await active_rulings(ctx, M.OUTLAW_RITE) if row.school is not None}


async def council_chained(ctx: TickContext, son_id: int) -> bool:
    return any(row.target_node_id == son_id and row.punishment is SonPunishment.CHAIN for row in await active_rulings(ctx, M.PUNISH_SON))


async def assigned_world(ctx: TickContext, son_id: int) -> int | None:
    if not await active_rulings(ctx, M.DIVIDE_WORLDS):
        return None
    found: int | None = await ctx.session.scalar(select(WorldRow.id).where(WorldRow.patron_son_id == son_id).order_by(WorldRow.id).limit(1))
    return found
