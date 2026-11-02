import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus

DEAD_STATUSES = (EntityStatus.REJECTED, EntityStatus.DESTROYED)
MIN_MENTION_LETTERS = 3


def usable(entity: EntityRow | None) -> bool:
    return entity is not None and entity.status not in DEAD_STATUSES


async def entities_in_text(session: AsyncSession, text: str, world_id: int, exclude: int) -> list[EntityRow]:
    if not text:
        return []
    candidates = await session.scalars(select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.id != exclude))
    found = []
    for entity in candidates:
        if len(entity.name) >= MIN_MENTION_LETTERS and re.search(rf"(?<![^\W\d_]){re.escape(entity.name)}(?![^\W\d_])", text):
            found.append(entity)
    return found
