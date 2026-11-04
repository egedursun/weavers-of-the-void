from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.polity import MortalReputeRow
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int


async def repute_of(session: AsyncSession, mortal_id: int) -> MortalReputeRow:
    found = await session.get(MortalReputeRow, mortal_id)
    if found is None:
        found = MortalReputeRow(mortal_entity_id=mortal_id, honour=PERCENT // 2, infamy=0, updated_epoch=0, locked=[])
        session.add(found)
    return found


async def shift_honour(ctx: TickContext, mortal_id: int, delta: int) -> int:
    row = await repute_of(ctx.session, mortal_id)
    if "honour" not in row.locked:
        row.honour = clamp_int(row.honour + delta, 0, PERCENT)
        row.updated_epoch = ctx.epoch
    return row.honour


async def shift_infamy(ctx: TickContext, mortal_id: int, delta: int) -> int:
    row = await repute_of(ctx.session, mortal_id)
    if "infamy" not in row.locked:
        row.infamy = clamp_int(row.infamy + delta, 0, PERCENT)
        row.updated_epoch = ctx.epoch
    return row.infamy
