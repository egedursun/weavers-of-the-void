from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.methods import METHODS, MethodSpec, default_method
from aerona.db.tables.industry import CommunityMethodRow
from aerona.domain.enums.industry import ProcessKind
from aerona.engine.kinds.nature import chosen_method


async def method_of(session: AsyncSession, community_id: int, process: ProcessKind) -> MethodSpec:
    chosen = select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == community_id, CommunityMethodRow.process == process)
    row = await session.scalar(chosen)
    return await chosen_method(session, row.method_kind_id, METHODS[row.method]) if row is not None else default_method(process)
