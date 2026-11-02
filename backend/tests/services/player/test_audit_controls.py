from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import CultStats
from aerona.services.player import canon, creatures, life_cycles
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, bond, make_entity, make_son


async def test_a_thread_moves_forward_by_hand(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    opened = await canon.open_thread(scope, canon.OpenThread(text="The salt war looms.", related_ids=(city.id,)))
    thread_id = opened.values["thread_id"]
    assert isinstance(thread_id, int)
    await canon.advance_thread(scope, canon.AdvanceThread(thread_id=thread_id, entity_id=city.id))
    thread = await session.get(ThreadRow, thread_id)
    assert thread is not None and thread.progress == 1


async def test_an_epoch_record_is_rewritten(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    session.add(EpochRow(epoch=1, name="Old name", narrative="Old story."))
    await session.flush()
    await canon.edit_epoch(scope, canon.EditEpoch(epoch=1, name="The Age of Salt", narrative="Salt rose."))
    row = await session.get(EpochRow, 1)
    assert row is not None and (row.name, row.narrative) == ("The Age of Salt", "Salt rose.")


async def test_native_life_is_seeded_by_hand(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    effect = await creatures.seed(scope, creatures.LifeSeed(world_id=world.world.id))
    assert effect.created_ids


async def test_a_sect_breaks_from_a_cult(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    patron = await make_son(session, "Velkar", world.world.id)
    rival = await make_son(session, "Ithren", world.world.id)
    stats = CultStats(followers=400, zeal=80, influence=40, devotion=30)
    cult = await make_entity(session, "Salt Choir", EntityType.CULT, world_id=world.world.id, stats=stats)
    await bond(session, cult.id, patron.id, BondKind.WORSHIPS)
    effect = await life_cycles.schism(scope, life_cycles.Schism(cult_id=cult.id, son_id=rival.id))
    assert effect.created_ids
