from sqlalchemy import delete, event, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.node import NameRegistryRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.naming import registered_pool
from aerona.rules.registry import Rules
from tests.db.factories import make_entity


async def test_the_name_pool_is_built_once_and_grows_with_each_new_name(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    reads: list[str] = []

    def counted(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        if "FROM name_registry" in statement and "SELECT name_registry.display" in statement:
            reads.append(statement)

    engine = session.sync_session.get_bind()
    event.listen(engine, "before_cursor_execute", counted)
    try:
        pool = await registered_pool(session, rules)
        for name in ("Velmor", "Tasken", "Orrin"):
            await make_entity(session, name, EntityType.REGION, world_id=world_id)
            assert await registered_pool(session, rules) is pool
            assert pool.is_taken(name)
    finally:
        event.remove(engine, "before_cursor_execute", counted)
    assert len(reads) == 1


async def test_a_name_taken_before_the_flush_is_already_in_the_pool(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    pool = await registered_pool(session, rules)
    session.add(NameRegistryRow(normalized="kessaray", node_id=world_id, display="Kessaray", single_word=True))
    assert pool.is_taken("Kessaray")
    session.expunge_all()


async def test_a_name_set_free_again_leaves_the_pool(session: AsyncSession, world_id: int) -> None:
    rules = Rules()
    region = await make_entity(session, "Velmor", EntityType.REGION, world_id=world_id)
    assert (await registered_pool(session, rules)).is_taken("Velmor")
    await session.execute(delete(NameRegistryRow).where(NameRegistryRow.node_id == region.id))
    assert not (await registered_pool(session, rules)).is_taken("Velmor")
    assert await session.scalar(select(NameRegistryRow).where(NameRegistryRow.node_id == region.id)) is None
