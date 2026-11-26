import json
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio import to_thread

from aerona.constants.books import (
    PDF_CHUNK_BYTES,
    PDF_FILENAME,
    PDF_MANIFEST,
    PDF_MOST_WORKERS,
    PDF_PROGRESS_IMAGES,
    PDF_PROGRESS_LAYOUT,
    PDF_PROGRESS_MERGE,
    PDF_PROGRESS_MODEL,
    PDF_PROGRESS_PRINT,
    PDF_STAGE_IMAGES,
    PDF_STAGE_MEASURE,
    PDF_STAGE_MERGE,
    PDF_STAGE_MODEL,
    PDF_STAGE_PRINT,
)
from aerona.core.errors import ConflictError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.engine.parallel.pool import workers_for
from aerona.jobs.context import JobContext
from aerona.services.books.assets import write_images, write_maps
from aerona.services.books.cache import cached_book
from aerona.services.books.chunks import split_book
from aerona.services.books.render import PdfState, PrintLinks, render_book
from aerona.services.books.title import titled, universe_title
from aerona.services.books.typeset import Typesetter, bind
from aerona.services.container import Services

NO_WORLD = "There is no world to print yet."
DOWNLOAD_URL = "/api/book.pdf"
MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class PdfManifest:
    epoch: int
    created_at: str
    size: int


def pdf_path(services: Services) -> Path:
    return services.settings.exports_dir / PDF_FILENAME


def _manifest_path(services: Services) -> Path:
    return services.settings.exports_dir / PDF_MANIFEST


def read_manifest(services: Services) -> PdfManifest | None:
    path = _manifest_path(services)
    if not path.is_file() or not pdf_path(services).is_file():
        return None
    try:
        return PdfManifest(**json.loads(path.read_text()))
    except (ValueError, TypeError):
        return None


def pdf_state(services: Services, epoch: int) -> PdfState:
    manifest = read_manifest(services)
    if manifest is None:
        return PdfState(ready=False, stale=False, url=DOWNLOAD_URL, size_mb=0.0, epoch=None, world_epoch=epoch)
    return PdfState(
        ready=True, stale=manifest.epoch != epoch, url=DOWNLOAD_URL, size_mb=round(manifest.size / MEGABYTE, 1), epoch=manifest.epoch, world_epoch=epoch
    )


def stage(context: JobContext, start: float, end: float, label: str) -> Callable[[float], None]:
    context.report(start, label)
    return lambda share: context.report(start + (end - start) * share, label)


async def typeset(document: str, directory: Path, target: Path, *, workers: int, title: str, context: JobContext) -> None:
    book = await to_thread.run_sync(lambda: split_book(document, PDF_CHUNK_BYTES))
    setter = Typesetter(book, directory, workers, stage(context, PDF_PROGRESS_LAYOUT, PDF_PROGRESS_PRINT, PDF_STAGE_MEASURE))
    measured = await setter.measure()
    setter.report = stage(context, PDF_PROGRESS_PRINT, PDF_PROGRESS_MERGE, PDF_STAGE_PRINT)
    printed = await setter.print(measured)
    context.report(PDF_PROGRESS_MERGE, PDF_STAGE_MERGE)
    paths = [setter.pdf(number) for number in range(len(printed))]
    await to_thread.run_sync(lambda: bind(paths, printed, target, title))


async def build_pdf(services: Services, context: JobContext) -> dict[str, Any]:
    context.report(PDF_PROGRESS_MODEL, PDF_STAGE_MODEL)
    async with services.database.read() as session:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            raise ConflictError(NO_WORLD)
        rules = rules_from_snapshot(cosmos.rules_snapshot) if cosmos.rules_snapshot else services.rules.current
        epoch = cosmos.epoch
        model = titled(await cached_book(services.database, session, rules), services.settings)
    exports = services.settings.exports_dir
    exports.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=exports) as scratch:
        directory = Path(scratch)
        links = PrintLinks(directory)
        rendered = await to_thread.run_sync(lambda: render_book(model, rules, links=links))
        context.report(PDF_PROGRESS_IMAGES, PDF_STAGE_IMAGES)
        span = PDF_PROGRESS_LAYOUT - PDF_PROGRESS_IMAGES
        await write_images(services, links.images, lambda share: context.report(PDF_PROGRESS_IMAGES + span * share, PDF_STAGE_IMAGES))
        await write_maps(services, links.maps)
        target = directory / PDF_FILENAME
        await typeset(
            rendered.html,
            directory,
            target,
            workers=min(workers_for(rules), PDF_MOST_WORKERS),
            title=universe_title(services.settings, cosmos),
            context=context,
        )
        size = target.stat().st_size
        shutil.move(target, pdf_path(services))
    manifest = PdfManifest(epoch=epoch, created_at=datetime.now(UTC).isoformat(), size=size)
    _manifest_path(services).write_text(json.dumps(asdict(manifest)))
    return {"epoch": epoch, "size": size}
