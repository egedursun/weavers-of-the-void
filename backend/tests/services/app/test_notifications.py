from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.notes import last_chronicle_id
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services import notifications
from aerona.services.chronicle import ChronicleWriter
from aerona.services.notifications import NotificationRequest, Notifier
from tests.services.app.factories import Cosmos


def test_classification_rules() -> None:
    classify = notifications.classify_chronicle
    assert classify(ChronicleKind.FATE, "Prophecy fulfilled: the sea rose.", None, []) is NotificationCategory.PROPHECY
    assert classify(ChronicleKind.BIRTH, "A son was summoned.", 3, []) is NotificationCategory.BIRTH
    assert classify(ChronicleKind.BIRTH, "A people awoke.", 3, [5]) is None
    assert classify(ChronicleKind.BIRTH, "A legendary child was born.", None, [5]) is NotificationCategory.BIRTH
    assert classify(ChronicleKind.WORLD, "Armies met.", None, [], FeedCategory.WAR) is NotificationCategory.WAR
    assert classify(ChronicleKind.WORLD, "A child was born.", None, [], FeedCategory.LIFE) is None
    assert classify(ChronicleKind.REBELLION, "Ithren rebelled.", 1, []) is NotificationCategory.REBELLION


def test_error_titles_are_friendly() -> None:
    assert notifications.classify_error("HTTP 529 overloaded_error") is notifications.ErrorClass.OVERLOAD
    assert notifications.is_retryable_error("rate limit exceeded")
    assert not notifications.is_retryable_error("Invalid JSON in output")
    title, body = notifications.normalized_texts(NotificationCategory.ERROR, "Request timed out after 60s", None)
    assert title == "The model call took too long and timed out."
    assert body == "Request timed out after 60s"
    long_title, long_body = notifications.normalized_texts(NotificationCategory.WAR, "x" * 120, None)
    assert len(long_title) == 90
    assert long_body == "x" * 120


async def test_notify_respects_settings_and_publishes(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    bus = EventBus()
    notifier = Notifier(bus)
    assert await notifier.notify(session, rules, NotificationRequest(NotificationCategory.DISASTER, "A flood.")) is None
    row = await notifier.notify(session, rules, NotificationRequest(NotificationCategory.WAR, "A war began."))
    assert row is not None
    assert row.severity == 2
    assert bus.replay_after(0)[-1].kind is EventKind.NOTIFICATION_CREATED
    settings = await notifications.update_settings(session, {NotificationCategory.WAR: False})
    assert not settings[NotificationCategory.WAR]
    assert await notifier.notify(session, rules, NotificationRequest(NotificationCategory.WAR, "Another war.")) is None
    note = await notifier.creator_note(session, rules, "Remember the salt.", None, world.people.id)
    assert note.category is NotificationCategory.NOTE
    page = await notifications.list_notifications(session, limit=10)
    assert page.unread == 2
    assert [item.title for item in page.items] == ["Remember the salt.", "A war began."]
    assert await notifications.mark_read(session, every=True) == 2
    assert await notifications.unread_count(session) == 0


async def test_prune_keeps_severe_and_recent(session: AsyncSession, world: Cosmos) -> None:
    notifier = Notifier()
    rules = Rules()
    for index in range(4):
        await notifier.notify(session, rules, NotificationRequest(NotificationCategory.EPOCH, f"Epoch {index}", forced=True))
    await notifier.notify(session, rules, NotificationRequest(NotificationCategory.APOCALYPSE, "Doom nears."))
    page = await notifications.list_notifications(session, limit=50)
    first_ids = sorted(item.id for item in page.items)[:2]
    await notifications.mark_read(session, ids=first_ids)
    tight = replace(rules, notifications=replace(rules.notifications, read_kept=2, total_cap=2))
    removed = await notifications.prune_notifications(session, tight)
    assert removed == 3
    remaining = await notifications.list_notifications(session, limit=50)
    assert [item.title for item in remaining.items] == ["Doom nears.", "Epoch 3"]


async def test_chronicle_writer_notifies(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    writer = ChronicleWriter(Notifier())
    since = await last_chronicle_id(session)
    ctx = await manual_context(session, "test", rules)
    written = await record(
        ctx,
        "player.history",
        roles={IncidentRole.SUBJECT: world.region.id},
        facts={"account": "A great battle shook the plain."},
        kind=ChronicleKind.WAR,
        feed=FeedCategory.WAR,
    )
    assert written.row.year is not None
    assert await writer.notify_unclassified(session, rules, since) >= 1
    page = await notifications.list_notifications(session, limit=10)
    assert page.items[0].chronicle_id == written.row.id
    assert page.items[0].target_node_id == world.region.id
