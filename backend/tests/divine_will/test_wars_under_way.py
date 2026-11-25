from pathlib import Path

from aerona.db.repositories.wars import wars_under_way
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarCause, WarEnding, WarStatus
from aerona.domain.models.entity_stats import EventStats
from tests.conftest import OpenDatabase
from tests.tools.factories import make_entity, seed_realm


def ending_of(status: WarStatus) -> dict[str, object]:
    return {"ended_epoch": 2, "ending": WarEnding.PEACE} if status is WarStatus.ENDED else {}


async def test_a_mobilizing_war_is_under_way_and_an_ended_one_is_not(tmp_path: Path, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "wars.db")
    realm = await seed_realm(database)
    async with database.write() as session:
        for number, status in enumerate((WarStatus.MOBILIZING, WarStatus.ONGOING, WarStatus.ENDED)):
            event = await make_entity(session, f"War {number}", EntityType.EVENT, world_id=realm.cosmos.world_id, stats=EventStats())
            session.add(
                WarRow(
                    event_entity_id=event.id, world_id=realm.cosmos.world_id, cause=next(iter(WarCause)), started_epoch=1, status=status, **ending_of(status)
                )
            )
    async with database.read() as session:
        assert await wars_under_way(session) == 2
    await database.dispose()
