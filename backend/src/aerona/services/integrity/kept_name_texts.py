from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.kept_names import KEPT_NAME_FLAGS
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.services.names import mentions_name

KEPT_NAMES_FIXUP = "naming.kept_names_described"


async def requeue_kept_names(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, KEPT_NAMES_FIXUP) is not None:
        return 0
    kept = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag.in_(KEPT_NAME_FLAGS))
    requeued = 0
    for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(kept), EntityRow.pending_name.is_(False)).order_by(EntityRow.id)):
        if entity.description and not mentions_name(entity.description, entity.name):
            entity.pending_name = True
            entity.naming_attempts = 0
            requeued += 1
    session.add(AppliedFixupRow(key=KEPT_NAMES_FIXUP, result={"requeued": requeued}))
    await session.flush()
    return requeued
