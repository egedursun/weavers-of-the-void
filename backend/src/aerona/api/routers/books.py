import re
from collections import OrderedDict
from datetime import datetime
from typing import Any

from anyio import to_thread
from fastapi import APIRouter, Path, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse

from aerona.api.background import submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel, JobAccepted
from aerona.constants.api import (
    BOOK_CSP,
    BOOK_PATH,
    CODEX_FILENAME_SUFFIX,
    ERROR_DESCRIPTION,
    ERROR_SCHEMA_REF,
    IMMUTABLE_CACHE,
    JSON_CONTENT_TYPE,
    MARKDOWN_MEDIA_TYPE,
)
from aerona.constants.books import (
    CODEX_ARCHIVE_MEDIA_TYPE,
    CODEX_ARCHIVE_SUFFIX,
    FONT_MEDIA_TYPE,
    PDF_GROUP,
    PDF_MEDIA_TYPE,
    TERRAIN_CACHE_SIZE,
    TERRAIN_MEDIA_TYPE,
    TERRAIN_WIDTH,
)
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.job import JobKind
from aerona.jobs.context import JobContext
from aerona.services.books import book_page, codex_markdown
from aerona.services.books.codex_archive import build_codex_archive
from aerona.services.books.mapsvg import load_map
from aerona.services.books.pdf import build_pdf, pdf_path, pdf_state, read_manifest
from aerona.services.books.render import BRAND_LOGO, FONT_DIRECTORY, CodexLinks
from aerona.services.books.terrain import render_terrain
from aerona.services.exchange import stream_and_delete

router = APIRouter(tags=["books"])

UNSAFE_FILE_CHARACTERS = re.compile(r"[^A-Za-z0-9_-]+")
FALLBACK_NAME = "cosmos"
BOOK_FILENAME_SUFFIX = "-book.pdf"
NO_MAP = "This world has no map yet."
NO_FONT = "No such font."
NO_PDF = "The book has not been printed yet."
FONT_PATTERN = r"^[a-z0-9-]+\.ttf$"
LOGO_MEDIA_TYPE = "image/png"
TERRAIN_CACHE: OrderedDict[tuple[int, str], bytes] = OrderedDict()


class BookPdfStatus(ApiModel):
    ready: bool
    stale: bool
    size: int | None
    epoch: int | None
    world_epoch: int | None = None
    created_at: datetime | None
    job_id: str | None
    progress: float | None
    stage: str | None


def _file_stem(name: str | None) -> str:
    stem = UNSAFE_FILE_CHARACTERS.sub("-", name or "").strip("-")
    return stem or FALLBACK_NAME


@router.get("/codex.md", response_class=Response, responses={200: {"content": {"text/markdown": {}}}})
async def codex(request: Request, services: ServicesDep) -> Response:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).get()
        text = await codex_markdown(session, rules, CodexLinks(base=str(request.base_url)))
    name = f"{_file_stem(cosmos.name if cosmos else None)}{CODEX_FILENAME_SUFFIX}"
    return Response(content=text, media_type=MARKDOWN_MEDIA_TYPE, headers={"content-disposition": f'attachment; filename="{name}"'})


@router.get("/codex.zip", response_class=StreamingResponse, responses={200: {"content": {CODEX_ARCHIVE_MEDIA_TYPE: {}}}})
async def codex_archive(services: ServicesDep) -> StreamingResponse:
    links = CodexLinks()
    async with reader(services) as session:
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).get()
        text = await codex_markdown(session, rules, links)
    stem = _file_stem(cosmos.name if cosmos else None)
    archive = await build_codex_archive(services, text, links, stem)
    headers = {"content-disposition": f'attachment; filename="{stem}{CODEX_ARCHIVE_SUFFIX}"', "content-length": str(archive.stat().st_size)}
    return StreamingResponse(stream_and_delete(archive), media_type=CODEX_ARCHIVE_MEDIA_TYPE, headers=headers)


@router.get(
    BOOK_PATH,
    response_class=HTMLResponse,
    responses={"default": {"description": ERROR_DESCRIPTION, "content": {JSON_CONTENT_TYPE: {"schema": {"$ref": ERROR_SCHEMA_REF}}}}},
)
async def book(services: ServicesDep, son_id: int | None = Query(default=None, ge=1), entity_id: int | None = Query(default=None, ge=1)) -> HTMLResponse:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).get()
        state = pdf_state(services, cosmos.epoch) if cosmos else None
        rendered = await book_page(session, rules, son_id=son_id, entity_id=entity_id, pdf=state)
    return HTMLResponse(rendered.html, headers={"content-security-policy": BOOK_CSP.format(nonce=rendered.nonce), "x-content-type-options": "nosniff"})


@router.get(f"{BOOK_PATH}/maps/{{world_id}}.jpg", response_class=Response, responses={200: {"content": {TERRAIN_MEDIA_TYPE: {}}}})
async def book_map(services: ServicesDep, world_id: int = Path(ge=1)) -> Response:
    async with reader(services) as session:
        loaded = await load_map(session, world_id)
    if loaded is None:
        raise NotFoundError(NO_MAP)
    world_map, signature = loaded
    key = (world_id, signature)
    data = TERRAIN_CACHE.get(key)
    if data is None:
        data = await to_thread.run_sync(render_terrain, world_map, TERRAIN_WIDTH)
        TERRAIN_CACHE[key] = data
        while len(TERRAIN_CACHE) > TERRAIN_CACHE_SIZE:
            TERRAIN_CACHE.popitem(last=False)
    TERRAIN_CACHE.move_to_end(key)
    return Response(content=data, media_type=TERRAIN_MEDIA_TYPE, headers={"cache-control": IMMUTABLE_CACHE, "x-content-type-options": "nosniff"})


@router.get(f"{BOOK_PATH}/fonts/{{file_name}}", response_class=FileResponse, include_in_schema=False)
async def book_font(file_name: str = Path(pattern=FONT_PATTERN)) -> FileResponse:
    path = FONT_DIRECTORY / file_name
    if not path.is_file():
        raise NotFoundError(NO_FONT)
    return FileResponse(path, media_type=FONT_MEDIA_TYPE, headers={"cache-control": IMMUTABLE_CACHE})


@router.get(f"{BOOK_PATH}/brand/logo.png", response_class=FileResponse, include_in_schema=False)
async def book_logo() -> FileResponse:
    return FileResponse(BRAND_LOGO, media_type=LOGO_MEDIA_TYPE, headers={"cache-control": IMMUTABLE_CACHE})


@router.get(f"{BOOK_PATH}/pdf", response_model=BookPdfStatus)
async def book_pdf_status(services: ServicesDep) -> BookPdfStatus:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).get()
    manifest = read_manifest(services)
    job_id = services.jobs.busy_group(PDF_GROUP)
    context = services.jobs.running_context(job_id) if job_id else None
    return BookPdfStatus(
        ready=manifest is not None,
        stale=manifest is not None and cosmos is not None and manifest.epoch != cosmos.epoch,
        size=manifest.size if manifest else None,
        epoch=manifest.epoch if manifest else None,
        world_epoch=cosmos.epoch if cosmos is not None else None,
        created_at=datetime.fromisoformat(manifest.created_at) if manifest else None,
        job_id=job_id,
        progress=context.progress if context else None,
        stage=context.stage if context else None,
    )


@router.post(f"{BOOK_PATH}/pdf", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def print_book(services: ServicesDep) -> JobAccepted:
    async def work(context: JobContext) -> dict[str, Any]:
        return await build_pdf(services, context)

    return await submit(services, JobKind.BOOK, PDF_GROUP, work, label="printing the book")


@router.get(f"{BOOK_PATH}.pdf", response_class=FileResponse, responses={200: {"content": {PDF_MEDIA_TYPE: {}}}})
async def download_book(services: ServicesDep) -> FileResponse:
    path = pdf_path(services)
    if read_manifest(services) is None or not path.is_file():
        raise NotFoundError(NO_PDF)
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).get()
    name = f"{_file_stem(cosmos.name if cosmos else None)}{BOOK_FILENAME_SUFFIX}"
    return FileResponse(path, media_type=PDF_MEDIA_TYPE, filename=name)
