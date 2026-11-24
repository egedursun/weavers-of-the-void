from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.community_relations import change_relation, set_relation
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_relation_with_a_god_is_never_written_as_a_community_relation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    await change_relation(ctx, world.people.id, world.son.id, -12, MemoryKind.ILL_WILL, note="a relation left untended")
    await set_relation(ctx, world.son.id, world.people.id, 40, "set by hand")
    await session.flush()
    rows = list(await session.scalars(select(CommunityRelationRow).where(CommunityRelationRow.entity_b_id == world.son.id)))
    rows += list(await session.scalars(select(CommunityRelationRow).where(CommunityRelationRow.entity_a_id == world.son.id)))
    assert rows == []


async def test_two_communities_still_keep_their_relation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    before = await change_relation(ctx, world.people.id, town.id, 0, MemoryKind.GOODWILL)
    after = await change_relation(ctx, world.people.id, town.id, 30, MemoryKind.GOODWILL)
    assert after > before
