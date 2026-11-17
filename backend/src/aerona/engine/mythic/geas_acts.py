from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memoized
from aerona.db.tables.mythic import GeasRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import GeasMode, GeasState
from aerona.engine.context import TickContext


def break_geas(row: GeasRow, epoch: int) -> None:
    row.state, row.broken_epoch = GeasState.BROKEN, epoch


@memoized(GeasRow)
async def kept_geas_acts(session: AsyncSession) -> frozenset[tuple[int, ActKind]]:
    found = await session.execute(select(GeasRow.bearer_entity_id, GeasRow.act).where(GeasRow.state == GeasState.KEPT))
    return frozenset((bearer, act) for bearer, act in found)


async def geas_acted(ctx: TickContext, actor_id: int, act: ActKind) -> int:
    if held(actor_id):
        return 0
    if (actor_id, act) not in await kept_geas_acts(ctx.session):
        return 0
    rows = list(await ctx.session.scalars(select(GeasRow).where(GeasRow.bearer_entity_id == actor_id, GeasRow.act == act, GeasRow.state == GeasState.KEPT)))
    for row in rows:
        if row.mode is GeasMode.TABOO and "state" not in row.locked:
            break_geas(row, ctx.epoch)
        elif row.mode is GeasMode.DUTY and "last_kept_epoch" not in row.locked:
            row.last_kept_epoch = ctx.epoch
    return len(rows)
