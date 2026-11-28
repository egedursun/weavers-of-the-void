import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.renames import rename_everywhere

EPOCH_TAG = re.compile(r"\s*\((?:Epoch|epoch) \d+\)$")


async def events_named_by_epoch(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.EVENT).order_by(EntityRow.id))
    return [event_id for event_id, name in rows if EPOCH_TAG.search(name) is not None and not held(event_id)]


async def name_event_plainly(session: AsyncSession, event_id: int) -> None:
    row = await session.get(EntityRow, event_id)
    if row is not None and EPOCH_TAG.search(row.name) is not None:
        await rename_everywhere(session, event_id, EPOCH_TAG.sub("", row.name), free=True)
