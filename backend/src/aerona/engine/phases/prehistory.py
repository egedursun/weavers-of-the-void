from sqlalchemy import select

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.prehistory import PrehistoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.prehistory import PrehistoryKind, PrehistoryState
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.prehistory.digest import dreams_of


@reads("table.chronicle", "table.incidents", "table.prehistories", "table.prehistory_events", "table.worlds")
@writes("table.prehistory_events")
async def dreamt_pasts(ctx: TickContext) -> None:
    rows = await ctx.session.scalars(
        select(PrehistoryRow).where(PrehistoryRow.kind == PrehistoryKind.DREAMT, PrehistoryRow.state == PrehistoryState.DONE).order_by(PrehistoryRow.world_id)
    )
    for row in list(rows):
        world = await ctx.session.get(WorldRow, row.world_id)
        if world is None or held(world.id):
            continue
        ctx.count("dreamt_events", await dreams_of(ctx, row, world, this_epoch=True))


PHASES = (Phase("dreamt_pasts", dreamt_pasts),)
