from pathlib import Path
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.rules.registry import Rules
from aerona.services.books.model import build_book
from aerona.services.books.render import BookOutline, CodexLinks, PdfState, RenderedBook, ScreenLinks, render_codex, render_shell
from aerona.services.books.title import universe_title
from aerona.services.books.worker import BookOrder, codex, in_books, order_for, outline, page, part, warm
from aerona.settings import Settings


async def book_title(session: AsyncSession, settings: Settings | None) -> str:
    return universe_title(settings, await CosmosRepository(session).get()) if settings is not None else ""


WRITTEN: WeakKeyDictionary[Database, dict[tuple[str | None, str], int]] = WeakKeyDictionary()


def mark_written(database: Database, order: BookOrder, links: ScreenLinks) -> None:
    WRITTEN.setdefault(database, {})[(links.universe, order.title)] = order.generation


def written(database: Database, order: BookOrder, links: ScreenLinks) -> bool:
    return WRITTEN.get(database, {}).get((links.universe, order.title)) == order.generation


async def book_page(
    database: Database,
    session: AsyncSession,
    rules: Rules,
    *,
    son_id: int | None = None,
    entity_id: int | None = None,
    pdf: PdfState | None = None,
    links: ScreenLinks | None = None,
    settings: Settings | None = None,
    wait: bool = True,
) -> RenderedBook:
    screen = links or ScreenLinks()
    order = order_for(database, rules, await book_title(session, settings))
    whole = son_id is None and entity_id is None
    if whole and not wait and not written(database, order, screen):
        return render_shell(order.title, screen, pdf, None, None)
    rendered = await in_books(database, page, order, son_id, entity_id, pdf, screen)
    if whole:
        mark_written(database, order, screen)
    return rendered


async def book_outline(database: Database, session: AsyncSession, rules: Rules, links: ScreenLinks, settings: Settings | None) -> BookOutline | None:
    order = order_for(database, rules, await book_title(session, settings))
    found = await in_books(database, outline, order, links)
    mark_written(database, order, links)
    return found


async def book_part(
    database: Database, session: AsyncSession, rules: Rules, links: ScreenLinks, *, number: int, generation: int | None, settings: Settings | None
) -> str:
    order = order_for(database, rules, await book_title(session, settings))
    return await in_books(database, part, order, links, number, generation)


async def write_book_parts(database: Database, session: AsyncSession, rules: Rules, links: ScreenLinks, settings: Settings | None) -> None:
    order = order_for(database, rules, await book_title(session, settings))
    if await in_books(database, warm, order, links):
        mark_written(database, order, links)


async def codex_markdown(session: AsyncSession, rules: Rules, links: CodexLinks) -> str:
    return render_codex(await build_book(session, rules), rules, links)


async def codex_file(database: Database, session: AsyncSession, rules: Rules, links: CodexLinks, folder: Path, *, settings: Settings | None = None) -> Path:
    order = order_for(database, rules, await book_title(session, settings))
    name, filled = await in_books(database, codex, order, links, str(folder))
    links.images.update(filled.images)
    links.maps.update(filled.maps)
    links.heavens.update(filled.heavens)
    return Path(name)
