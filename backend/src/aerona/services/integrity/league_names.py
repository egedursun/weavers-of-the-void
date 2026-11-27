import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import definite
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType

LEAGUE_NAME = re.compile(r"^the league of (?P<member>.+)$")


def proper_league_name(name: str) -> str | None:
    found = LEAGUE_NAME.match(name)
    if found is None:
        return None
    proper = f"the league of {definite(found.group('member'))}"
    return proper if proper != name else None


async def leagues_without_article(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LEAGUE).order_by(EntityRow.id))
    return [row.id for row in rows if not held(row.id) and proper_league_name(row.name) is not None]


async def name_league_properly(session: AsyncSession, league_id: int) -> None:
    league = await session.get(EntityRow, league_id)
    proper = proper_league_name(league.name) if league is not None else None
    if proper is not None:
        await NameRepository(session).rename(league_id, proper, free=True)


CLIQUE_PHRASE = " under those around "


async def offshoots_named_after_a_clique(session: AsyncSession) -> list[int]:
    rows = await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.name.contains(CLIQUE_PHRASE)).order_by(NodeRow.id))
    return [node for node, _ in rows if not held(node)]


async def name_offshoot_after_its_leader(session: AsyncSession, node_id: int) -> None:
    node = await session.get(NodeRow, node_id)
    if node is not None and CLIQUE_PHRASE in node.name:
        await NameRepository(session).rename(node_id, node.name.replace(CLIQUE_PHRASE, " under "), free=True)
