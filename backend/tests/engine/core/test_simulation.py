from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.pipeline import simulate
from tests.engine.core.factories import add_empty_world, seed_core_world


async def census(database: Database) -> dict[EntityType, int]:
    async with database.read() as session:
        rows = await session.execute(select(EntityRow.entity_type, func.count()).where(EntityRow.status == EntityStatus.CANON).group_by(EntityRow.entity_type))
        return {entity_type: int(count) for entity_type, count in rows}


async def test_a_seeded_world_fills_itself(database: Database) -> None:
    async with database.write() as session:
        await seed_core_world(session)
        await add_empty_world(session)
    before = await census(database)
    runs = await simulate(database, 6)
    after = await census(database)
    assert len(runs) == 6
    assert after.get(EntityType.PEOPLE, 0) > before.get(EntityType.PEOPLE, 0)
    assert after.get(EntityType.MORTAL, 0) > before.get(EntityType.MORTAL, 0)
    assert after.get(EntityType.SETTLEMENT, 0) > before.get(EntityType.SETTLEMENT, 0)
