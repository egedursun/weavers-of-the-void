from sqlalchemy import text

from aerona.db.book_marks import changes_the_book, past_stamp, rewrites_the_past
from aerona.db.session import Database


def test_only_writes_to_what_the_book_shows_change_it() -> None:
    assert changes_the_book('UPDATE "entities" SET name = ? WHERE id = ?')
    assert changes_the_book("INSERT OR IGNORE INTO chronicle (text) VALUES (?)")
    assert changes_the_book("WITH gone AS (SELECT 1) DELETE FROM bonds WHERE id IN gone")
    assert not changes_the_book("UPDATE jobs SET progress = ? WHERE id = ?")
    assert not changes_the_book("INSERT INTO notifications (title) VALUES (?)")
    assert not changes_the_book("SELECT * FROM entities")


async def test_a_write_the_book_does_not_show_leaves_it_current(database: Database) -> None:
    before = database.book_generation
    async with database.write() as session:
        await session.execute(text("UPDATE notifications SET severity = severity"))
        await session.execute(text("UPDATE jobs SET progress = progress"))
    assert database.book_generation == before
    async with database.write() as session:
        await session.execute(text("UPDATE cosmos SET name = name"))
    assert database.book_generation == before + 1


def test_only_a_rewrite_of_recorded_changes_rewrites_the_past() -> None:
    assert rewrites_the_past("UPDATE state_changes SET season = ? WHERE id = ?")
    assert rewrites_the_past('DELETE FROM "state_change_terms" WHERE change_id = ?')
    assert rewrites_the_past("INSERT OR REPLACE INTO state_changes (id) VALUES (?)")
    assert rewrites_the_past("WITH gone AS (SELECT 1) DELETE FROM state_changes WHERE id IN gone")
    assert not rewrites_the_past("INSERT INTO state_changes (epoch) VALUES (?)")
    assert not rewrites_the_past('UPDATE "entities" SET name = ? WHERE id = ?')


async def test_a_committed_rewrite_of_the_past_renews_its_stamp(database: Database) -> None:
    before = past_stamp(database.url)
    async with database.write() as session:
        await session.execute(text("UPDATE state_changes SET season = season"))
    rewritten = past_stamp(database.url)
    assert rewritten != before
    async with database.write() as session:
        await session.execute(text("UPDATE cosmos SET name = name"))
    assert past_stamp(database.url) == rewritten
