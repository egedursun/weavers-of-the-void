from pathlib import Path

from aerona.db.tables.cosmos import CosmosRow
from aerona.events.bus import EventBus
from aerona.events.change_feed import TrackedTable
from aerona.services.application import build_application, epoch_end_maintenance, stop_application
from aerona.services.rules import RulesService
from aerona.services.state import change_digest
from aerona.settings import Settings
from tests.conftest import OpenDatabase
from tests.services.app.factories import seed_cosmos


async def test_application_tracks_changes_and_maintains(tmp_path: Path, open_database: OpenDatabase) -> None:
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False)
    settings.ensure_directories()
    database = open_database(settings.database_path)
    rules = RulesService(database)
    await rules.load()
    application = await build_application(settings, database, EventBus(), rules)
    token = application.feed.version
    async with database.write() as session:
        world = await seed_cosmos(session)
        people_id = world.people.id
    changes = application.feed.changes_since(token, 1000)
    assert not changes.full
    assert str(people_id) in changes.changed(TrackedTable.ENTITIES)
    async with database.read() as session:
        digest = await change_digest(session, rules.current, changes)
    assert people_id in {entity.id for entity in digest.entities}
    assert digest.cosmos_changed
    token = application.feed.version
    async with database.write() as session:
        cosmos = await session.get(CosmosRow, 1)
        assert cosmos is not None
        cosmos.doom_clock = 5
    assert not application.feed.changes_since(token, 1000).touched(TrackedTable.COSMOS)
    counters = await epoch_end_maintenance(application, database, rules.current, 1)
    assert counters["importance"] >= 1
    assert "data_repairs" in counters and "schema_repairs" in counters
    await application.world_changed.fire("World replaced.")
    assert application.feed.changes_since(token, 1000).full
    await stop_application(application)
    await database.dispose()
