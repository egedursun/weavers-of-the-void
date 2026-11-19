from collections.abc import Collection

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.titles import TitleHolderRow, TitleProfileRow


async def title_prestige(session: AsyncSession, holders: Collection[int]) -> dict[int, int]:
    if not holders:
        return {}
    rows = await session.execute(
        select(TitleHolderRow.holder_node_id, func.sum(TitleProfileRow.prestige))
        .join(TitleProfileRow, TitleProfileRow.title_entity_id == TitleHolderRow.title_entity_id)
        .where(TitleHolderRow.holder_node_id.in_(sorted(holders)), TitleHolderRow.until_epoch.is_(None), TitleProfileRow.destroyed_epoch.is_(None))
        .group_by(TitleHolderRow.holder_node_id)
    )
    return {int(holder): int(prestige or 0) for holder, prestige in rows if holder is not None}
