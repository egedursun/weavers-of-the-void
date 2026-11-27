from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.war import WarStatus


async def realm_parties(session: AsyncSession, polity_id: int) -> set[int]:
    profile = await session.get(PolityProfileRow, polity_id)
    found = {polity_id}
    if profile is not None:
        found |= {node for node in (profile.core_entity_id, profile.capital_entity_id) if node is not None}
    return found


async def foes_of(session: AsyncSession, nodes: set[int]) -> set[int]:
    if not nodes:
        return set()
    mine, theirs = aliased(WarSideRow), aliased(WarSideRow)
    rows = await session.scalars(
        select(theirs.entity_id)
        .join(mine, (mine.war_id == theirs.war_id) & (mine.side != theirs.side))
        .join(WarRow, WarRow.id == mine.war_id)
        .where(mine.entity_id.in_(sorted(nodes)), WarRow.status != WarStatus.ENDED, mine.left_epoch.is_(None), theirs.left_epoch.is_(None))
    )
    return set(rows)


async def heads_a_foe(session: AsyncSession, mortal_id: int, polity_id: int) -> bool:
    headed = set(await session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == mortal_id)))
    return bool(await foes_of(session, headed) & await realm_parties(session, polity_id))


async def serves_a_foe(session: AsyncSession, mortal_ids: list[int], org_id: int) -> set[int]:
    foes = await foes_of(session, {org_id})
    if not foes or not mortal_ids:
        return set()
    serving: set[int] = set()
    for holder, polity in await session.execute(
        select(OfficeRow.holder_entity_id, OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id.in_(sorted(set(mortal_ids))))
    ):
        if holder is not None and await realm_parties(session, polity) & foes:
            serving.add(holder)
    return serving
