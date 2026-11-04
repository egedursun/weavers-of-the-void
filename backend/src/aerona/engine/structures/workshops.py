from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import WorkshopRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.engine.context import TickContext


async def attach(session: AsyncSession, community_id: int, kind: WorkshopKind, structure_id: int, epoch: int) -> WorkshopRow:
    row = await session.scalar(
        select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.kind == kind).order_by(WorkshopRow.id).limit(1)
    )
    if row is None:
        row = WorkshopRow(community_entity_id=community_id, kind=kind, level=1, built_epoch=max(1, epoch), structure_entity_id=structure_id)
        session.add(row)
    elif row.structure_entity_id is None:
        row.structure_entity_id = structure_id
    await session.flush()
    return row


async def link_workshop(ctx: TickContext, community_id: int, kind: WorkshopKind, structure_id: int) -> WorkshopRow:
    return await attach(ctx.session, community_id, kind, structure_id, ctx.epoch)


async def unlink(session: AsyncSession, structure_id: int) -> None:
    for row in await session.scalars(select(WorkshopRow).where(WorkshopRow.structure_entity_id == structure_id)):
        row.structure_entity_id = None
