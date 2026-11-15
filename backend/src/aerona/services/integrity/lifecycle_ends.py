from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.lifecycle.ends import KIND_OF_TYPE, seed_state
from aerona.rules.registry import Rules


async def seed_missing_states(session: AsyncSession, rules: Rules, epoch: int) -> int:
    del rules
    mended = 0
    for row in list(await session.scalars(select(LifecycleStateRow))):
        holder = await session.get(EntityRow, row.holder_entity_id)
        if holder is None or KIND_OF_TYPE.get(holder.entity_type) is not row.kind:
            await session.delete(row)
            mended += 1
    known = set(await session.scalars(select(LifecycleStateRow.holder_entity_id)))
    for holder in list(
        await session.scalars(
            select(EntityRow).where(EntityRow.entity_type.in_(list(KIND_OF_TYPE)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if holder.id not in known:
            await seed_state(session, holder, epoch)
            mended += 1
    await session.flush()
    return mended
