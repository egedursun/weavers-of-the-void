import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.renames import rename_everywhere

DOUBLED = re.compile(r"\blaw law\b", re.IGNORECASE)


async def laws_named_twice(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.LAW).order_by(EntityRow.id))
    return [law_id for law_id, name in rows if DOUBLED.search(name) is not None and not held(law_id)]


async def name_law_once(session: AsyncSession, law_id: int) -> None:
    row = await session.get(EntityRow, law_id)
    if row is not None and DOUBLED.search(row.name) is not None:
        await rename_everywhere(session, law_id, DOUBLED.sub("law", row.name), free=True)
