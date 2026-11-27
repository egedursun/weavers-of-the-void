from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.engine.primitives.renames import derived_names, follow_derived

NAME_TABLE = "nodes"
NAME_FIELD = "name"


async def renames(session: AsyncSession) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    rows = await session.execute(
        select(StateChangeRow.node_id, StateChangeRow.before_text)
        .where(StateChangeRow.table_name == NAME_TABLE, StateChangeRow.field == NAME_FIELD, StateChangeRow.before_text.is_not(None))
        .order_by(StateChangeRow.id)
    )
    for node_id, before in rows:
        if node_id is not None and before:
            found.setdefault(node_id, []).append(before)
    return found


async def stale_derived_names(session: AsyncSession) -> list[int]:
    stale: list[int] = []
    for node_id, olds in (await renames(session)).items():
        node = await session.get(NodeRow, node_id)
        if node is None or held(node_id):
            continue
        for old in olds:
            if old != node.name and await derived_names(session, node_id, old):
                stale.append(node_id)
                break
    return stale


async def follow_old_names(session: AsyncSession, node_id: int) -> None:
    node = await session.get(NodeRow, node_id)
    if node is None:
        return
    for old in (await renames(session)).get(node_id, []):
        if old != node.name:
            await follow_derived(session, node_id, old, node.name, None)
