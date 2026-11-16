from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.domain.enums.foreign_god import ForeignGodStatus, PantheonStructure
from aerona.engine.divine.pantheon import blend, fade_and_return, form_pantheons, structure_for
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_arcana_w15 import foreign_caster
from tests.engine.core.test_minds_w44 import at


async def test_a_lone_god_heads_its_world_and_a_pair_stands_as_one(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    god = await foreign_caster(session, world)
    assert structure_for([god]) is PantheonStructure.SINGLE_HIGH_GOD
    assert structure_for([god, god]) is PantheonStructure.DUAL
    assert await form_pantheons(ctx) == 1
    row = await session.get(PantheonStructureRow, world.world.id)
    assert row is not None and row.head_node_id == god.id


async def test_a_forgotten_god_falls_asleep(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    god = await foreign_caster(session, world)
    god.faith = 1
    assert await fade_and_return(ctx) == 1
    assert god.status is ForeignGodStatus.ASLEEP


async def test_gods_held_as_one_pass_faith_to_the_dominant(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    god = await foreign_caster(session, world)
    god.faith, world.son.faith = 10, 0
    joined = SyncretismRow(foreign_god_id=god.id, son_id=world.son.id, people_entity_id=world.people.id, dominant_node_id=world.son.id, since_epoch=1)
    joined.locked = []
    session.add(joined)
    session.add(PantheonTieRow(god_node_id=world.son.id, other_node_id=god.id, locked=[]))
    await session.flush()
    await blend(ctx)
    assert world.son.faith > 0
    assert god.faith < 10
