from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.mortal.life import CHILD_SUBTYPE, adult


async def grown_children(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(EntityRow.id, MortalProfileRow.life_stage)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.subtype == CHILD_SUBTYPE)
        .order_by(EntityRow.id)
    )
    return [node for node, stage in rows if adult(stage)]


async def drop_child_label(session: AsyncSession, key: int) -> None:
    mortal = await session.get(EntityRow, key)
    if mortal is not None and mortal.subtype == CHILD_SUBTYPE:
        mortal.subtype = None
