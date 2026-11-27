from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mind import MemoryRow
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


async def test_the_doer_never_remembers_its_own_deed_as_done_to_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    wronged = await settlement(session, "Wrongedholm", world, world.regions[0])
    partner = await settlement(session, "Partnerholm", world, world.regions[0])
    await change_relation(ctx, wronged.id, world.people.id, -20, MemoryKind.BETRAYED_ME, note="broke the treaty")
    await change_relation(ctx, partner.id, world.people.id, 15, MemoryKind.TRADED_WITH)
    await session.flush()
    held = {(row.holder_node_id, row.subject_node_id): row.kind for row in await session.scalars(select(MemoryRow))}
    assert held[(wronged.id, world.people.id)] is MemoryKind.BETRAYED_ME
    assert held[(world.people.id, wronged.id)] is not MemoryKind.BETRAYED_ME
    assert held[(world.people.id, partner.id)] is MemoryKind.TRADED_WITH
