from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mortal import MortalProfileRow
from aerona.engine.context import TickContext
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.mortal.standing import add_honour, add_infamy


async def repute_of(session: AsyncSession, mortal_id: int, epoch: int = 0) -> MortalProfileRow:
    row, _ = await ensure_profile(session, mortal_id, epoch)
    return row


async def shift_honour(ctx: TickContext, mortal_id: int, delta: int) -> int:
    return (await add_honour(ctx.session, mortal_id, delta, ctx.epoch)).honour


async def shift_infamy(ctx: TickContext, mortal_id: int, delta: int) -> int:
    return (await add_infamy(ctx.session, mortal_id, delta, ctx.epoch)).infamy
