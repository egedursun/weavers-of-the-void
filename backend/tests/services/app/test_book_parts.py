import re
from collections import Counter

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.books import BOOK_PARTS_KEPT
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.rules.registry import Rules
from aerona.services.books import WRITTEN, book_outline, book_page, book_part, worker
from aerona.services.books.ledger_parts import SLICES
from aerona.services.books.model import build_book
from aerona.services.books.render import ScreenLinks, render_book
from tests.services.app.factories import Cosmos
from tests.services.app.test_books import enrich

SMALL_PART = 3000
OUTLINE = re.compile(r'<script type="application/json" id="book-outline">')
HOLDER = re.compile(r'<div class="book-part" data-part="(\d+)"')
TAG = re.compile(r"<[^>]+>")
NONCE = re.compile(r'nonce="[^"]*"')
ID = re.compile(r"""\sid=["']([^"']+)["']""")


def main_of(html: str) -> str:
    return html[html.index("<main>") + len("<main>") : html.rindex("</main>")]


def text_of(html: str) -> str:
    return " ".join(TAG.sub(" ", html).split())


@pytest.fixture
def small_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker, "BOOK_PART_BYTES", SMALL_PART)
    worker.PARTS.clear()


async def test_the_book_page_opens_with_its_first_part_and_loads_the_rest_without_losing_a_word(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos, small_parts: None
) -> None:
    links = ScreenLinks()
    shell = await book_page(database, session, rules, links=links)
    outline = await book_outline(database, session, rules, links, None)
    assert outline is not None and len(outline.sizes) > 2
    assert OUTLINE.search(shell.html)
    assert [int(found) for found in HOLDER.findall(shell.html)] == list(range(len(outline.sizes)))
    bodies = [
        await book_part(database, session, rules, links, number=number, generation=outline.generation, settings=None) for number in range(len(outline.sizes))
    ]
    whole = main_of(render_book(worker.model_of(worker.order_for(database, rules, "")), rules, links=links).html)
    assert text_of("".join(bodies)) == text_of(whole)
    ids = Counter(found for body in bodies for found in ID.findall(body))
    assert ids == Counter(ID.findall(whole))
    assert all(outline.anchors[found] == number for number, body in enumerate(bodies) for found in ID.findall(body))
    with pytest.raises(NotFoundError):
        await book_part(database, session, rules, links, number=len(outline.sizes), generation=outline.generation, settings=None)


async def test_a_page_opened_before_the_book_changed_is_told_to_reload(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos, small_parts: None
) -> None:
    links = ScreenLinks()
    first = await book_outline(database, session, rules, links, None)
    assert first is not None
    for _ in range(BOOK_PARTS_KEPT + 1):
        database.gate.book_generation += 1
        await book_outline(database, session, rules, links, None)
    with pytest.raises(ConflictError):
        await book_part(database, session, rules, links, number=0, generation=first.generation, settings=None)


async def test_the_server_answers_the_book_page_at_once_while_the_book_is_still_being_written(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos, small_parts: None
) -> None:
    links = ScreenLinks()
    database.gate.book_generation += 1
    waiting = await book_page(database, session, rules, links=links, wait=False)
    assert 'id="book-preparing"' in waiting.html and 'id="pdf-make"' not in waiting.html and not OUTLINE.search(waiting.html)
    await book_outline(database, session, rules, links, None)
    ready = await book_page(database, session, rules, links=links, wait=False)
    assert OUTLINE.search(ready.html) and 'id="book-preparing"' not in ready.html


async def test_a_changed_world_opens_the_last_written_book_at_once_and_offers_the_newer_one(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos, small_parts: None
) -> None:
    links = ScreenLinks()
    first = await book_outline(database, session, rules, links, None)
    assert first is not None
    database.gate.book_generation += 1
    older = await book_page(database, session, rules, links=links, wait=False)
    assert 'id="book-newer"' in older.html and f'data-generation="{first.generation}"' in older.html and OUTLINE.search(older.html)
    newer = await book_outline(database, session, rules, links, None)
    assert newer is not None and newer.generation == first.generation + 1
    current = await book_page(database, session, rules, links=links, wait=False)
    assert 'id="book-newer"' not in current.html and f'data-generation="{newer.generation}"' in current.html


async def test_a_restarted_server_opens_the_book_it_kept_on_disk_at_once(
    database: Database, session: AsyncSession, rules: Rules, world: Cosmos, small_parts: None
) -> None:
    links = ScreenLinks()
    written = await book_outline(database, session, rules, links, None)
    assert written is not None
    first = await book_part(database, session, rules, links, number=0, generation=written.generation, settings=None)
    worker.PARTS.clear()
    WRITTEN.clear()
    reopened = await book_page(database, session, rules, links=links, wait=False)
    assert 'id="book-newer"' in reopened.html and 'data-generation="-1"' in reopened.html
    assert await book_part(database, session, rules, links, number=0, generation=-1, settings=None) == first


async def test_the_book_written_in_slices_reads_exactly_as_the_book_written_whole(
    session: AsyncSession, rules: Rules, world: Cosmos, monkeypatch: pytest.MonkeyPatch
) -> None:
    await enrich(session, world)
    await session.flush()
    assert int(await session.scalar(select(func.count()).select_from(StateChangeRow)) or 0) >= 3 * 3
    whole = NONCE.sub("", render_book(await build_book(session, rules), rules).html)
    monkeypatch.setattr(SLICES, "count", 3)
    sliced = NONCE.sub("", render_book(await build_book(session, rules), rules).html)
    assert sliced == whole
