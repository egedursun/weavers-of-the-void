from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import KEEP_KEY
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import UnitTypeStats
from aerona.engine.collective.embodied import mark
from tests.engine.core.factories import CoreWorld, entity


async def test_a_made_kind_that_ends_while_the_cosmos_is_unread_takes_its_epoch_before_any_flush(session: AsyncSession, world: CoreWorld) -> None:
    kind = await entity(session, "Shield Line", EntityType.UNIT_TYPE, UnitTypeStats(), world_id=world.world.id, birth_epoch=2)
    await session.flush()
    session.expunge_all()
    session.sync_session.info[KEEP_KEY] = []
    kind = await session.get_one(EntityRow, kind.id)
    await mark(session, kind, EntityStatus.DEAD)
    await session.flush()
    assert kind.status is EntityStatus.DEAD and kind.end_epoch is not None and kind.end_epoch >= kind.birth_epoch


async def test_a_rejected_record_that_returns_as_dead_takes_its_epoch_before_its_bonds_are_reopened(session: AsyncSession, world: CoreWorld) -> None:
    record = await entity(session, "Old Banner", EntityType.UNIT_TYPE, UnitTypeStats(), world_id=world.world.id)
    repository = EntityRepository(session)
    await repository.set_status(record, EntityStatus.REJECTED, 3)
    await repository.set_status(record, EntityStatus.DEAD, 4)
    assert record.status is EntityStatus.DEAD and record.end_epoch == 4
