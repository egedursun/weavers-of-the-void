from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.rules.registry import Rules
from aerona.services.books.model import build_book
from aerona.services.books.render import CodexLinks, PdfState, RenderedBook, ScreenLinks, render_codex
from aerona.services.books.title import universe_title
from aerona.services.books.worker import codex, in_books, order_for, page
from aerona.settings import Settings


async def book_title(session: AsyncSession, settings: Settings | None) -> str:
    return universe_title(settings, await CosmosRepository(session).get()) if settings is not None else ""


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
) -> RenderedBook:
    order = order_for(database, rules, await book_title(session, settings))
    return await in_books(database, page, order, son_id, entity_id, pdf, links)


async def codex_markdown(session: AsyncSession, rules: Rules, links: CodexLinks) -> str:
    return render_codex(await build_book(session, rules), rules, links)


async def codex_file(database: Database, session: AsyncSession, rules: Rules, links: CodexLinks, folder: Path, *, settings: Settings | None = None) -> Path:
    order = order_for(database, rules, await book_title(session, settings))
    name, filled = await in_books(database, codex, order, links, str(folder))
    links.images.update(filled.images)
    links.maps.update(filled.maps)
    links.heavens.update(filled.heavens)
    return Path(name)
