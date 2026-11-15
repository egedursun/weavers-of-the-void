from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.prehistory import DeepTimeRunRow, PrehistoryEventRow, PrehistoryRow
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryState
from aerona.engine.prehistory.digest import backfill_world, lore_free
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules


async def mend_prehistories(session: AsyncSession, rules: Rules, epoch: int) -> int:
    del epoch
    mended = 0
    for row in list(await session.scalars(select(PrehistoryRow).where(PrehistoryRow.state == PrehistoryState.RUNNING))):
        row.state = PrehistoryState.ABORTED
        mended += 1
    for run in list(await session.scalars(select(DeepTimeRunRow).where(DeepTimeRunRow.state == DeepTimeState.RUNNING))):
        run.state = DeepTimeState.STOPPED
        mended += 1
    hollow = select(PrehistoryEventRow).where(PrehistoryEventRow.incident_id.is_(None), PrehistoryEventRow.subject_node_id.is_(None))
    for event in list(await session.scalars(hollow)):
        await session.delete(event)
        mended += 1
    ctx = await manual_context(session, "prehistory_backfill", rules)
    known = set(await session.scalars(select(PrehistoryRow.world_id)))
    for world in list(await session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if world.id not in known and not await lore_free(ctx, world.id):
            await backfill_world(ctx, world)
            mended += 1
    await session.flush()
    return mended
