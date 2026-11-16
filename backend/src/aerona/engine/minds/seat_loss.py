from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow, MindSeatRow, MindStateRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.minds import MindSeat
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.records import retire_in

SEATED_ELSEWHERE = frozenset({MindSeat.OBJECT, MindSeat.STRUCTURE, MindSeat.NETWORK, MindSeat.HOST, MindSeat.REALM, MindSeat.MEDIUM})


async def name_of(ctx: TickContext, node_id: int) -> str:
    entity = await ctx.session.get(EntityRow, node_id)
    return entity.name if entity is not None else "a mind"


async def seat_lost(ctx: TickContext, row: MindProfileRow) -> bool:
    if row.seat_node_id is not None and row.seat_node_id != row.node_id and row.seat in SEATED_ELSEWHERE:
        seat = await ctx.session.get(EntityRow, row.seat_node_id)
        dimension = await ctx.session.get(MadeRealmRow, row.seat_node_id) if row.seat is MindSeat.REALM else None
        if (seat is None or seat.status is not EntityStatus.CANON) and dimension is None:
            return True
    vital = select(MindSeatRow.part_node_id).where(MindSeatRow.mind_node_id == row.node_id, MindSeatRow.vital.is_(True))
    for part in await ctx.session.scalars(vital):
        found = await ctx.session.get(EntityRow, part)
        if found is None or found.status is not EntityStatus.CANON:
            return True
    return False


async def lose_seat(ctx: TickContext, row: MindProfileRow) -> None:
    saved = await ctx.session.scalar(select(MindStateRow.id).where(MindStateRow.mind_node_id == row.node_id).limit(1))
    name = await name_of(ctx, row.node_id)
    row.seat, row.seat_node_id = MindSeat.NONE, None
    if saved is not None:
        row.dormant = True
        await note(ctx, f"{name} lost its seat; only what was saved of it remains.", key="mind.seat_lost", ids=[row.node_id])
        return
    entity = await ctx.session.get(EntityRow, row.node_id)
    if entity is not None and entity.status is EntityStatus.CANON:
        await retire_in(ctx, entity, "its mind ended with its seat")
    await note(ctx, f"The mind of {name} ended with its seat.", key="mind.ended", ids=[row.node_id])
