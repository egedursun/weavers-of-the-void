from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.made import AugmentEffectRow, AugmentRow
from aerona.domain.enums.made import EffectTarget


async def bonus(session: AsyncSession, node_id: int | None, target: EffectTarget, key: str) -> int:
    if node_id is None:
        return 0
    statement = (
        select(func.coalesce(func.sum(AugmentEffectRow.amount), 0))
        .join(AugmentRow, AugmentRow.id == AugmentEffectRow.augment_id)
        .where(AugmentRow.bearer_node_id == node_id, AugmentEffectRow.target == target, AugmentEffectRow.target_key == key)
    )
    return int(await session.scalar(statement) or 0)
