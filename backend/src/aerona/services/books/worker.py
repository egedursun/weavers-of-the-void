import asyncio
import hashlib
import json
import multiprocessing
import os
import re
import tempfile
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from weakref import WeakKeyDictionary

from sqlalchemy.engine import make_url

from aerona.constants.books import BOOK_PART_BYTES, BOOK_PARTS_KEPT
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.off_loop import BOOK_THREADS
from aerona.db.session import Database
from aerona.engine.parallel.pool import exit_with_parent
from aerona.rules.registry import Rules
from aerona.services.books.chunks import Splitter, StreamSplitter
from aerona.services.books.ledger_parts import SLICES
from aerona.services.books.model import BookModel, ChronicleLine, build_book, entry_chronicle
from aerona.services.books.records import RowStore
from aerona.services.books.render import (
    BookLinks,
    BookOutline,
    CodexLinks,
    PdfState,
    RenderedBook,
    ScreenLinks,
    book_pieces,
    codex_chunks,
    find_entity,
    find_son,
    render_book,
    render_entry,
    render_shell,
)

NO_WORLD = "There is no world yet."
NO_ENTRY = "No such entry in the book."
NO_PART = "The book has no such part."
BOOK_CHANGED = "The book has changed since this page opened. Reload the page to read the newest book."
KEPT_FOLDER = "book-parts"
SLICES_LEAST = 2
SLICES_MOST = 8
SPARE_CORES = 2
KEY_LENGTH = 16
KEPT_GENERATION = -1
ANCHOR = re.compile(r"""\sid=["']([^"']+)["']""")


@dataclass(frozen=True)
class BookOrder:
    url: str
    generation: int
    rules: Rules
    title: str


MODELS: dict[str, tuple[int, BookModel | None]] = {}


@dataclass(frozen=True)
class BookParts:
    title: str
    outline: BookOutline
    store: RowStore
    offsets: tuple[int, ...]

    def body(self, number: int) -> str:
        if not 0 <= number < len(self.offsets):
            raise NotFoundError(NO_PART)
        return self.store.read(self.offsets[number])


PARTS: dict[tuple[str, str | None, str], dict[int, BookParts]] = {}


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


def kept_paths(order: BookOrder, links: ScreenLinks) -> tuple[Path, Path]:
    folder = Path(make_url(order.url).database or tempfile.gettempdir()).parent / KEPT_FOLDER
    key = hashlib.sha256(f"{links.universe}|{order.title}".encode()).hexdigest()[:KEY_LENGTH]
    return folder / f"{key}.parts", folder / f"{key}.json"


def written_parts(model: BookModel, order: BookOrder, links: ScreenLinks) -> BookParts:
    body_path, outline_path = kept_paths(order, links)
    body_path.parent.mkdir(parents=True, exist_ok=True)
    writing = body_path.with_suffix(".writing")
    writing.unlink(missing_ok=True)
    store = RowStore(writing)
    anchors: dict[str, int] = {}
    offsets: list[int] = []
    sizes: list[int] = []
    streamer = StreamSplitter(Splitter(BOOK_PART_BYTES, keep_ids=False))
    for piece in book_pieces(model, order.rules, links):
        for body in streamer.push(piece):
            for anchor in ANCHOR.findall(body):
                anchors.setdefault(anchor, len(offsets))
            offsets.append(store.append(body))
            sizes.append(len(body.encode()))
    store.flush()
    os.replace(writing, body_path)
    outline = BookOutline(order.generation, tuple(sizes), anchors)
    outline_path.write_text(json.dumps({"title": model.title, "sizes": sizes, "anchors": anchors, "offsets": offsets}), encoding="utf-8")
    return BookParts(model.title, outline, store, tuple(offsets))


def kept_parts(order: BookOrder, links: ScreenLinks) -> BookParts | None:
    body_path, outline_path = kept_paths(order, links)
    if not body_path.exists() or not outline_path.exists():
        return None
    try:
        kept = json.loads(outline_path.read_text(encoding="utf-8"))
        return BookParts(kept["title"], BookOutline(KEPT_GENERATION, tuple(kept["sizes"]), dict(kept["anchors"])), RowStore(body_path), tuple(kept["offsets"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def parts_of(order: BookOrder, links: ScreenLinks, generation: int | None = None) -> BookParts | None:
    kept = PARTS.setdefault((order.url, links.universe, order.title), {})
    if generation == KEPT_GENERATION and KEPT_GENERATION not in kept:
        saved = kept_parts(order, links)
        if saved is not None:
            kept[KEPT_GENERATION] = saved
    if generation is not None:
        found = kept.get(generation)
        if found is None:
            raise ConflictError(BOOK_CHANGED)
        return found
    found = kept.get(order.generation)
    if found is None:
        model = model_of(order)
        if model is None:
            return None
        found = kept[order.generation] = written_parts(model, order, links)
        kept.pop(KEPT_GENERATION, None)
        while len(kept) > BOOK_PARTS_KEPT:
            kept.pop(min(kept))
    return found


def warm(order: BookOrder, links: ScreenLinks) -> bool:
    return parts_of(order, links) is not None


def outline(order: BookOrder, links: ScreenLinks) -> BookOutline | None:
    parts = parts_of(order, links)
    return parts.outline if parts is not None else None


def part(order: BookOrder, links: ScreenLinks, number: int, generation: int | None) -> str:
    parts = parts_of(order, links, generation)
    if parts is None:
        raise NotFoundError(NO_WORLD)
    return parts.body(number)


def written_page(order: BookOrder, links: ScreenLinks, pdf: PdfState | None, generation: int | None) -> RenderedBook | None:
    kept = PARTS.setdefault((order.url, links.universe, order.title), {})
    if generation is None:
        saved = kept.get(KEPT_GENERATION) or kept_parts(order, links)
        if saved is None:
            return None
        generation = kept.setdefault(KEPT_GENERATION, saved).outline.generation
    found = kept.get(generation)
    if found is None:
        return None
    return render_shell(found.title, links, pdf, found.body(0), found.outline, stale=True)


def page(order: BookOrder, son_id: int | None, entity_id: int | None, pdf: PdfState | None, links: ScreenLinks | None) -> RenderedBook:
    screen = links or ScreenLinks()
    if son_id is None and entity_id is None:
        parts = parts_of(order, screen)
        if parts is None:
            return render_book(None, order.rules, links=screen)
        return render_shell(parts.title, screen, pdf, parts.body(0), parts.outline)
    model = model_of(order)
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


def slice_count() -> int:
    return max(SLICES_LEAST, min(SLICES_MOST, (os.cpu_count() or SLICES_LEAST) - SPARE_CORES))


def book_start(parent: int) -> None:
    exit_with_parent(parent)
    count = slice_count()
    SLICES.use(
        ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context("spawn"), initializer=exit_with_parent, initargs=(os.getpid(),)), count
    )


class BookProcess:
    def __init__(self) -> None:
        self.pool = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"), initializer=book_start, initargs=(os.getpid(),))

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
    return BookOrder(database.url, database.book_generation, rules, title)
