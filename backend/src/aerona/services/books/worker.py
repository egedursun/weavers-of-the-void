import asyncio
import multiprocessing
import os
import tempfile
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from weakref import WeakKeyDictionary

from aerona.core.errors import NotFoundError
from aerona.db.off_loop import BOOK_THREADS
from aerona.db.session import Database
from aerona.engine.parallel.pool import exit_with_parent
from aerona.rules.registry import Rules
from aerona.services.books.model import BookModel, ChronicleLine, build_book, entry_chronicle
from aerona.services.books.render import (
    BookLinks,
    CodexLinks,
    PdfState,
    RenderedBook,
    ScreenLinks,
    codex_chunks,
    find_entity,
    find_son,
    render_book,
    render_entry,
)

NO_WORLD = "There is no world yet."
NO_ENTRY = "No such entry in the book."


@dataclass(frozen=True)
class BookOrder:
    url: str
    generation: int
    rules: Rules
    title: str


MODELS: dict[str, tuple[int, BookModel | None]] = {}


def read_book[T](url: str, reading: Callable[[Database], Awaitable[T]]) -> T:
    async def run() -> T:
        database = Database(url)
        try:
            return await reading(database)
        finally:
            await database.close()

    return asyncio.run(run())


async def fresh_model(database: Database, rules: Rules) -> BookModel | None:
    async with database.read() as session:
        return await build_book(session, rules)


def model_of(order: BookOrder) -> BookModel | None:
    found = MODELS.get(order.url)
    if found is None or found[0] != order.generation:
        MODELS[order.url] = found = (order.generation, read_book(order.url, lambda database: fresh_model(database, order.rules)))
    model = found[1]
    return replace(model, title=order.title) if model is not None and order.title else model


def warm(order: BookOrder) -> bool:
    return model_of(order) is not None


def page(order: BookOrder, son_id: int | None, entity_id: int | None, pdf: PdfState | None, links: ScreenLinks | None) -> RenderedBook:
    model = model_of(order)
    if son_id is None and entity_id is None:
        return render_book(model, order.rules, links=links, pdf=pdf)
    if model is None:
        raise NotFoundError(NO_WORLD)
    son = find_son(model, son_id) if son_id is not None else None
    entity = find_entity(model, entity_id) if entity_id is not None else None
    if son is None and entity is None:
        raise NotFoundError(NO_ENTRY)

    async def chronicle(database: Database) -> list[ChronicleLine]:
        async with database.read() as session:
            return await entry_chronicle(session, son_id=son.son.id if son else None, entity_id=entity.entity.id if entity else None)

    lines = read_book(order.url, chronicle)
    return render_entry(replace(model, single_chronicle=lines), order.rules, son=son, entity=entity, links=links)


def codex(order: BookOrder, links: CodexLinks, folder: str) -> tuple[str, CodexLinks]:
    model = model_of(order)
    Path(folder).mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(suffix=".md", dir=folder)
    os.close(handle)
    with Path(name).open("w", encoding="utf-8") as out:
        for chunk in codex_chunks(model, order.rules, links):
            out.write(chunk)
    return name, links


def print_html[L: BookLinks](order: BookOrder, links: L) -> tuple[RenderedBook, L]:
    return render_book(model_of(order), order.rules, links=links), links


class BookProcess:
    def __init__(self) -> None:
        self.pool = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"), initializer=exit_with_parent, initargs=(os.getpid(),))

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)


PROCESSES: WeakKeyDictionary[Database, BookProcess] = WeakKeyDictionary()


def books_of(database: Database) -> Executor:
    if not database.work_in_processes:
        return BOOK_THREADS
    found = PROCESSES.get(database)
    if found is None:
        found = PROCESSES[database] = BookProcess()
    return found.pool


def close_books(database: Database) -> None:
    found = PROCESSES.pop(database, None)
    if found is not None:
        found.close()


async def in_books[T](database: Database, call: Callable[..., T], *args: object) -> T:
    return await asyncio.get_running_loop().run_in_executor(books_of(database), partial(call, *args))


def order_for(database: Database, rules: Rules, title: str) -> BookOrder:
    return BookOrder(database.url, database.generation, rules, title)
