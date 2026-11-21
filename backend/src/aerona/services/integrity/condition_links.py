from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.customs import people_of


async def system_present(session: AsyncSession, row: ConditionRow) -> bool:
    kind = await session.get(AgentlessConditionRow, row.kind_id) if row.kind_id is not None else None
    bearer = await session.get(EntityRow, row.bearer_node_id)
    if kind is None or bearer is None:
        return True
    people = await people_of(session, bearer)
    if people is None:
        return True
    systems = list(await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == people.id)))
    return not systems or any(system.system is kind.system and system.present for system in systems)


async def absent_systems(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ConditionRow).where(ConditionRow.kind_id.is_not(None), ConditionRow.ended_epoch.is_(None)).order_by(ConditionRow.id))
    return [row.id for row in rows if not await system_present(session, row)]


async def unkind_condition(session: AsyncSession, key: int) -> None:
    row = await session.get(ConditionRow, key)
    if row is not None:
        row.kind_id = None
