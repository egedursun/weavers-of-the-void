from aerona.domain.enums.chronicle import FeedCategory
from aerona.events.change_feed import ChangeFeed, ChangeOperation, TrackedTable
from aerona.events.feed_categories import feed_category


def test_versions_and_incremental_changes() -> None:
    feed = ChangeFeed(period="p1")
    start = feed.version
    feed.record("entities", "5", ChangeOperation.INSERT)
    feed.record("entities", "5", ChangeOperation.UPDATE)
    feed.record("sons", "2", ChangeOperation.DELETE)
    feed.record("ignored_table", "1", ChangeOperation.INSERT)
    changes = feed.changes_since(start, 100)
    assert not changes.full
    assert changes.changed(TrackedTable.ENTITIES) == ("5",)
    assert changes.deleted(TrackedTable.SONS) == ("2",)
    assert feed.version == "p1:3"


def test_full_refresh_cases() -> None:
    feed = ChangeFeed(period="p1")
    assert feed.changes_since("other:0", 10).full
    assert feed.changes_since("garbage", 10).full
    token = feed.version
    for index in range(5):
        feed.record("bonds", str(index), ChangeOperation.INSERT)
    assert feed.changes_since(token, 3).full
    feed.reset()
    assert feed.changes_since(token, 100).full
    after_reset = feed.version
    feed.record("bonds", "9", ChangeOperation.INSERT)
    assert feed.changes_since(after_reset, 100).changed(TrackedTable.BONDS) == ("9",)


def test_prune_keeps_newest() -> None:
    feed = ChangeFeed(period="p")
    for index in range(10):
        feed.record("chronicle", str(index), ChangeOperation.INSERT)
    assert feed.prune(4) == 6
    assert feed.size == 4
    assert feed.changes_since("p:2", 100).full


def test_feed_categories() -> None:
    assert feed_category("war.outbreak", "anything") is FeedCategory.WAR
    assert feed_category(None, "A comet crossed the sky.") is FeedCategory.SKY
    assert feed_category(None, "The warden slept.") is FeedCategory.WORLD
    assert feed_category("unknown.key", "The plague spread.") is FeedCategory.DISASTER
