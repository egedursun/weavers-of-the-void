from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import FOR_THE_DEAD, GATHERING_COLLECTIONS, GUEST_ROLES
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow, GatheringRow
from aerona.db.write_guard import held
from aerona.domain.enums.gathering import GuestRole

MOURNED = GUEST_ROLES[GuestRole.MOURNED]


async def rites_in_another_dead(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(GatheringRow.id, GatheringRow.honoured_node_id, GatheringRow.collection_id, GatheringRow.locked)
        .where(GatheringRow.kind.in_(sorted(FOR_THE_DEAD)), GatheringRow.collection_id.is_not(None), GatheringRow.honoured_node_id.is_not(None))
        .order_by(GatheringRow.id)
    )
    mourned = {
        (collection, node)
        for collection, node in await session.execute(
            select(CollectionMemberRow.collection_id, CollectionMemberRow.node_id).where(CollectionMemberRow.role == MOURNED)
        )
    }
    return [
        row_id
        for row_id, honoured, collection, locked in rows
        if (collection, honoured) not in mourned and "collection_id" not in (locked or []) and not held(honoured)
    ]


async def file_rite_under_its_dead(session: AsyncSession, row_id: int) -> None:
    row = await session.get(GatheringRow, row_id)
    if row is None or row.honoured_node_id is None:
        return
    own = select(CollectionMemberRow.collection_id).where(CollectionMemberRow.node_id == row.honoured_node_id, CollectionMemberRow.role == MOURNED)
    row.collection_id = await session.scalar(
        select(CollectionRow.id).where(CollectionRow.kind == GATHERING_COLLECTIONS[row.kind], CollectionRow.id.in_(own)).order_by(CollectionRow.id).limit(1)
    )
