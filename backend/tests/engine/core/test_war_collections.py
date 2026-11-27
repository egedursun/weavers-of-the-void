from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.engine.history.collections import CollectionTally, join_or_open
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement


async def test_each_war_gathers_its_own_happenings_even_when_a_side_fights_two_wars(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "war_collections", Rules())
    shared, first, second = [await settlement(session, name, world, world.regions[0]) for name in ("Keelmouth", "Reedholm", "Saltby")]
    tally = CollectionTally()
    pair = {shared.id: CollectionRole.LEADER, first.id: CollectionRole.VICTIM}
    other = {shared.id: CollectionRole.LEADER, second.id: CollectionRole.VICTIM}
    one = await join_or_open(
        ctx, CollectionKind.WAR, world_id=world.world.id, members=pair, places=[], source_key="war.outbreak", tally=tally, name="War of Keelmouth and Reedholm"
    )
    two = await join_or_open(
        ctx, CollectionKind.WAR, world_id=world.world.id, members=other, places=[], source_key="war.outbreak", tally=tally, name="War of Keelmouth and Saltby"
    )
    again = await join_or_open(
        ctx, CollectionKind.WAR, world_id=world.world.id, members=pair, places=[], source_key="war.battle", tally=tally, name="War of Keelmouth and Reedholm"
    )
    assert one is not None and two is not None and again is not None
    assert one.id != two.id and again.id == one.id
    assert (one.name, two.name) == ("War of Keelmouth and Reedholm", "War of Keelmouth and Saltby")
