from sqlalchemy import ColumnElement, and_, delete, select

from aerona.db.tables.loops import LoopSignalRow
from aerona.db.write_guard import held
from aerona.domain.enums.loops import BalanceLoop
from aerona.engine.context import TickContext


def delay_of(ctx: TickContext, loop: BalanceLoop) -> int:
    found: int = getattr(ctx.rules.loops, "delay_" + loop.value)
    return found


def signal_of(loop: BalanceLoop, holder_id: int, subject: int) -> ColumnElement[bool]:
    return and_(LoopSignalRow.loop == loop, LoopSignalRow.holder_node_id == holder_id, LoopSignalRow.subject == subject)


async def lagged[Value: (int, float)](ctx: TickContext, loop: BalanceLoop, holder_id: int | None, value: Value, subject: int = 0) -> Value:
    epochs = delay_of(ctx, loop)
    if epochs <= 0 or holder_id is None or held(holder_id):
        return value
    row = await ctx.session.get(LoopSignalRow, (loop, holder_id, subject, ctx.epoch))
    if row is None:
        ctx.session.add(LoopSignalRow(loop=loop, holder_node_id=holder_id, subject=subject, epoch=ctx.epoch, value=float(value)))
    else:
        row.value = float(value)
    signal = signal_of(loop, holder_id, subject)
    await ctx.session.execute(delete(LoopSignalRow).where(signal, LoopSignalRow.epoch < ctx.epoch - epochs))
    past = await ctx.session.scalar(
        select(LoopSignalRow.value).where(signal, LoopSignalRow.epoch <= ctx.epoch - epochs).order_by(LoopSignalRow.epoch.desc()).limit(1)
    )
    if past is None:
        past = await ctx.session.scalar(select(LoopSignalRow.value).where(signal).order_by(LoopSignalRow.epoch).limit(1))
    return type(value)(past if past is not None else value)
