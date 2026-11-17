from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow, MindSeatRow, MindStateRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.records import retire_in
from aerona.engine.recording.record import record as record_incident

SEATED_ELSEWHERE = frozenset({MindSeat.OBJECT, MindSeat.STRUCTURE, MindSeat.NETWORK, MindSeat.HOST, MindSeat.REALM, MindSeat.MEDIUM})


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
    row.seat, row.seat_node_id = MindSeat.NONE, None
    if saved is not None:
        row.dormant = True
        await record_incident(ctx, "mind.seat_lost", roles={IncidentRole.SUBJECT: row.node_id})
        return
    entity = await ctx.session.get(EntityRow, row.node_id)
    if entity is not None and entity.status is EntityStatus.CANON:
        await retire_in(ctx, entity, "its mind ended with its seat")
    await record_incident(ctx, "mind.ended", roles={IncidentRole.SUBJECT: row.node_id})
