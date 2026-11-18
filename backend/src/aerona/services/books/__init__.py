import os
import tempfile
from pathlib import Path

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.rules.registry import Rules
from aerona.services.books.model import BookModel, build_book, entry_chronicle
from aerona.services.books.render import CodexLinks, PdfState, RenderedBook, codex_chunks, find_entity, find_son, render_book, render_codex, render_entry


async def book_page(
    session: AsyncSession, rules: Rules, *, son_id: int | None = None, entity_id: int | None = None, pdf: PdfState | None = None
) -> RenderedBook:
    model = await build_book(session, rules)
    if son_id is None and entity_id is None:
        return render_book(model, rules, pdf=pdf)
    if model is None:
        raise NotFoundError("There is no world yet.")
    son = find_son(model, son_id) if son_id is not None else None
    entity = find_entity(model, entity_id) if entity_id is not None else None
    if son is None and entity is None:
        raise NotFoundError("No such entry in the book.")
    model.single_chronicle = await entry_chronicle(session, son_id=son.son.id if son else None, entity_id=entity.entity.id if entity else None)
    return render_entry(model, rules, son=son, entity=entity)


async def codex_markdown(session: AsyncSession, rules: Rules, links: CodexLinks) -> str:
    return render_codex(await build_book(session, rules), rules, links)


def write_codex(target: Path, model: BookModel | None, rules: Rules, links: CodexLinks) -> None:
    with target.open("w", encoding="utf-8") as out:
        for chunk in codex_chunks(model, rules, links):
            out.write(chunk)


async def codex_file(session: AsyncSession, rules: Rules, links: CodexLinks, folder: Path) -> Path:
    model = await build_book(session, rules)
    await to_thread.run_sync(lambda: folder.mkdir(parents=True, exist_ok=True))
    handle, name = tempfile.mkstemp(suffix=".md", dir=folder)
    os.close(handle)
    target = Path(name)
    await to_thread.run_sync(write_codex, target, model, rules, links)
    return target
