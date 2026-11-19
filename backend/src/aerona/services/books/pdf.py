import asyncio
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio import to_thread

from aerona.constants.books import (
    PDF_FILENAME,
    PDF_LIBRARY_DIRECTORIES,
    PDF_LIBRARY_VARIABLE,
    PDF_MANIFEST,
    PDF_PROGRESS_IMAGES,
    PDF_PROGRESS_LAYOUT,
    PDF_PROGRESS_MODEL,
    PDF_STAGE_IMAGES,
    PDF_STAGE_LAYOUT,
    PDF_STAGE_MODEL,
    PDF_WORKER_MODULE,
)
from aerona.core.errors import ConflictError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.jobs.context import JobContext
from aerona.services.books.assets import write_images, write_maps
from aerona.services.books.cache import cached_book
from aerona.services.books.render import PdfState, PrintLinks, render_book
from aerona.services.container import Services

NO_WORLD = "There is no world to print yet."
LAYOUT_FAILED = "The pages could not be set: {reason}"
DOWNLOAD_URL = "/api/book.pdf"
MEGABYTE = 1024 * 1024
ERROR_TAIL = 600


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


def _worker_environment() -> dict[str, str]:
    environment = dict(os.environ)
    if sys.platform == "darwin":
        present = [directory for directory in PDF_LIBRARY_DIRECTORIES if Path(directory).is_dir()]
        existing = environment.get(PDF_LIBRARY_VARIABLE)
        environment[PDF_LIBRARY_VARIABLE] = os.pathsep.join([*present, *([existing] if existing else [])])
    return environment


async def _layout(source: Path, target: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        PDF_WORKER_MODULE,
        str(source),
        str(target),
        env=_worker_environment(),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _out, error = await process.communicate()
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
    if process.returncode != 0 or not await to_thread.run_sync(target.is_file):
        reason = error.decode(errors="replace").strip().splitlines()[-1:] if error else []
        raise ConflictError(LAYOUT_FAILED.format(reason=(reason[0] if reason else f"exit {process.returncode}")[-ERROR_TAIL:]))


async def build_pdf(services: Services, context: JobContext) -> dict[str, Any]:
    context.report(PDF_PROGRESS_MODEL, PDF_STAGE_MODEL)
    async with services.database.read() as session:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            raise ConflictError(NO_WORLD)
        rules = rules_from_snapshot(cosmos.rules_snapshot) if cosmos.rules_snapshot else services.rules.current
        epoch = cosmos.epoch
        model = await cached_book(services.database, session, rules)
    exports = services.settings.exports_dir
    exports.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=exports) as scratch:
        directory = Path(scratch)
        links = PrintLinks(directory)
        rendered = await to_thread.run_sync(lambda: render_book(model, rules, links=links))
        source = directory / "book.html"
        source.write_text(rendered.html, encoding="utf-8")
        context.report(PDF_PROGRESS_IMAGES, PDF_STAGE_IMAGES)
        span = PDF_PROGRESS_LAYOUT - PDF_PROGRESS_IMAGES
        await write_images(services, links.images, lambda share: context.report(PDF_PROGRESS_IMAGES + span * share, PDF_STAGE_IMAGES))
        await write_maps(services, links.maps)
        context.report(PDF_PROGRESS_LAYOUT, PDF_STAGE_LAYOUT)
        target = directory / PDF_FILENAME
        await _layout(source, target)
        size = target.stat().st_size
        shutil.move(target, pdf_path(services))
    manifest = PdfManifest(epoch=epoch, created_at=datetime.now(UTC).isoformat(), size=size)
    _manifest_path(services).write_text(json.dumps(asdict(manifest)))
    return {"epoch": epoch, "size": size}
