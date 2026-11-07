from pathlib import Path

from sqlalchemy import select

from aerona.agents.metrics import TelemetrySink, current_actions, current_epoch, metrics_epoch, metrics_turn
from aerona.db.session import Database
from aerona.db.tables.meta import MapSnapshotRow, NotificationRow
from aerona.db.telemetry.tables import LlmCallRow
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.job import JobKind
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import JobManager
from aerona.llm.records import CallKind, CallRecord
from aerona.services.application import ApplicationServices, build_application, epoch_end_maintenance, schedule_completion, stop_application
from aerona.services.rules import RulesService
from aerona.settings import Settings
from tests.conftest import OpenDatabase
from tests.services.app.factories import seed_cosmos


async def open_application(open_database: OpenDatabase, tmp_path: Path, bus: EventBus) -> tuple[ApplicationServices, Database, RulesService]:
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False)
    settings.ensure_directories()
    database = open_database(settings.database_path)
    rules = RulesService(database)
    await rules.load()
    return await build_application(settings, database, bus, rules), database, rules


def forget_world(database_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def record() -> CallRecord:
    return CallRecord(label="Fate", model="m", kind=CallKind.STRUCTURED, duration_seconds=1.0, attempts=1)


async def test_calls_carry_the_epoch_and_old_epochs_are_pruned(tmp_path: Path, open_database: OpenDatabase) -> None:
    application, database, rules = await open_application(open_database, tmp_path, EventBus())
    late = rules.current.metrics.keep_epochs + 10
    assert current_epoch.get() is None and current_actions.get() is None
    with metrics_epoch(1):
        await TelemetrySink(application.telemetry)(record())
    with metrics_turn(late, 3):
        await TelemetrySink(application.telemetry)(record())
    async with application.telemetry.sessions() as session:
        rows = list(await session.scalars(select(LlmCallRow).order_by(LlmCallRow.id)))
    assert [(row.epoch, row.actions) for row in rows] == [(1, None), (late, 3)]
    assert [item.epoch for item in (await application.metrics.summary(5)).epochs] == [late, 1]
    removed = await application.metrics.prune()
    assert removed == 1
    await stop_application(application)
    await database.dispose()


async def test_events_are_stamped_persisted_and_restored(tmp_path: Path, open_database: OpenDatabase) -> None:
    bus = EventBus()
    application, database, _rules = await open_application(open_database, tmp_path, bus)
    async with database.write() as session:
        await seed_cosmos(session)
    bus.publish(EventKind.EPOCH_PROGRESS, {"epoch": 7, "no": 1})
    stamped = bus.publish(EventKind.SYSTEM_NOTE, {"text": "hello"})
    assert stamped.payload["epoch"] == 7
    await application.live_log.drain()
    await application.notification_stream.drain()
    await stop_application(application)
    await database.dispose()
    again = EventBus()
    reopened, database, _rules = await open_application(open_database, tmp_path, again)
    texts = [item.payload.get("text") for item in again.replay_after(0)]
    assert "hello" in texts
    assert again.last_id >= stamped.id
    await stop_application(reopened)
    await database.dispose()


async def test_a_replaced_world_never_shows_the_old_world_s_feed(tmp_path: Path, open_database: OpenDatabase) -> None:
    bus = EventBus()
    application, database, _rules = await open_application(open_database, tmp_path, bus)
    async with database.write() as session:
        await seed_cosmos(session)
    bus.publish(EventKind.SYSTEM_NOTE, {"text": "the old world"})
    await application.live_log.drain()
    await stop_application(application)
    await database.dispose()
    forget_world(Settings(data_dir=tmp_path / "data").database_path)
    empty = EventBus()
    reopened, database, _rules = await open_application(open_database, tmp_path, empty)
    assert [item.payload.get("text") for item in empty.replay_after(0)] == []
    async with database.write() as session:
        await seed_cosmos(session)
    empty.publish(EventKind.SYSTEM_NOTE, {"text": "the new world"})
    await reopened.live_log.drain()
    await reopened.world_changed.fire("the world was replaced")
    assert "the new world" not in [item.payload.get("text") for item in empty.replay_after(0)]
    await reopened.live_log.drain()
    await stop_application(reopened)
    await database.dispose()
    last = EventBus()
    final, database, _rules = await open_application(open_database, tmp_path, last)
    texts = [item.payload.get("text") for item in last.replay_after(0)]
    assert "the old world" not in texts and "the new world" in texts
    await stop_application(final)
    await database.dispose()


async def test_epoch_end_notification_error_notice_and_snapshot(tmp_path: Path, open_database: OpenDatabase) -> None:
    bus = EventBus()
    application, database, rules = await open_application(open_database, tmp_path, bus)
    async with database.write() as session:
        await seed_cosmos(session)
    bus.publish(EventKind.EPOCH_FINISHED, {"epoch": 3, "new_epoch": 4, "summary": {"epoch_name": "Dry Wells", "rejected": ["a"]}})
    bus.publish(EventKind.SYSTEM_ERROR, {"text": "invalid output schema", "will_retry": False, "son_id": None})
    bus.publish(EventKind.SYSTEM_ERROR, {"text": "overloaded", "will_retry": True})
    await application.notification_stream.drain()
    async with database.read() as session:
        notes = list(await session.scalars(select(NotificationRow)))
    categories = [note.category for note in notes]
    assert NotificationCategory.EPOCH in categories and categories.count(NotificationCategory.ERROR) == 1
    epoch_note = next(note for note in notes if note.category is NotificationCategory.EPOCH)
    assert epoch_note.body is not None and "Dry Wells" in epoch_note.body
    counters = await epoch_end_maintenance(application, database, rules.current, 4)
    assert counters["snapshots"] >= 1
    async with database.read() as session:
        assert list(await session.scalars(select(MapSnapshotRow.epoch))) == [4]
    await stop_application(application)
    await database.dispose()


async def test_startup_completion_hook_submits_a_job_when_work_is_missing(tmp_path: Path, open_database: OpenDatabase) -> None:
    application, database, rules = await open_application(open_database, tmp_path, EventBus())
    async with database.write() as session:
        await seed_cosmos(session)
    jobs = JobManager(database, EventBus())
    await schedule_completion(application, jobs, rules)
    recent = await jobs.list_recent(5)
    assert [job.kind for job in recent] == [JobKind.COMPLETION.value]
    await jobs.shutdown()
    await stop_application(application)
    await database.dispose()
