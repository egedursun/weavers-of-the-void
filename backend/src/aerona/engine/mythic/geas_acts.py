from sqlalchemy import select

from aerona.db.tables.mythic import GeasRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import GeasMode, GeasState
from aerona.engine.context import TickContext


def break_geas(row: GeasRow, epoch: int) -> None:
    row.state, row.broken_epoch = GeasState.BROKEN, epoch


async def geas_acted(ctx: TickContext, actor_id: int, act: ActKind) -> int:
    if held(actor_id):
        return 0
    rows = list(await ctx.session.scalars(select(GeasRow).where(GeasRow.bearer_entity_id == actor_id, GeasRow.act == act, GeasRow.state == GeasState.KEPT)))
    for row in rows:
        if row.mode is GeasMode.TABOO and "state" not in row.locked:
            break_geas(row, ctx.epoch)
        elif row.mode is GeasMode.DUTY and "last_kept_epoch" not in row.locked:
            row.last_kept_epoch = ctx.epoch
    return len(rows)
