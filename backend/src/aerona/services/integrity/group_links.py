from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.engine.creature_groups.groups import MIXED


async def foreign_leaders(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for group in await session.scalars(select(CreatureGroupRow).where(CreatureGroupRow.leader_node_id.is_not(None)).order_by(CreatureGroupRow.id)):
        if group.form in MIXED:
            continue
        profile = await session.get(BeastProfileRow, group.leader_node_id)
        if profile is not None and profile.species_entity_id not in {None, group.species_entity_id}:
            found.append(group.id)
    return found


async def unseat_leader(session: AsyncSession, key: int) -> None:
    group = await session.get(CreatureGroupRow, key)
    if group is not None:
        group.leader_node_id = None
