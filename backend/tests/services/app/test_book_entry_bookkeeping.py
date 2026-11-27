from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.db.tables.node import NodeRow
from aerona.services.books.typed import TypedIndex, title_of
from tests.services.app.factories import Cosmos

BOOKKEEPING_TITLES = frozenset(title_of(table) for table in BOOKKEEPING_TABLES)


async def test_an_entry_never_shows_a_bookkeeping_table(session: AsyncSession, world: Cosmos) -> None:
    names = {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name))}
    whole = await TypedIndex.load(session, names)
    single = await TypedIndex.load_node(session, names, world.people.id)
    titles = {section.title for sections in whole.sections.values() for section in sections} | {section.title for section in single.of(world.people.id)}
    assert names[world.people.id]
    assert titles & BOOKKEEPING_TITLES == set()
