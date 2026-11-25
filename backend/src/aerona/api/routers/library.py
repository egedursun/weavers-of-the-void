import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path as FilePath
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Path, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from aerona.api.schemas.common import Done
from aerona.api.schemas.library import (
    CoverFromMedia,
    CoverPaint,
    CoverPaintPrompt,
    ImportConfirm,
    LibraryEventPage,
    LibraryEventView,
    LibraryJobView,
    LibraryStreamEvent,
    PackagePreviewView,
    TrashEmptied,
    TrashEntryView,
    TrashPageView,
    UniverseCreate,
    UniverseDetail,
    UniverseDuplicate,
    UniverseFacets,
    UniverseList,
    UniverseOriginFacet,
    UniversePatch,
    UniverseStatusFacet,
    UniverseTagFacet,
    UniverseView,
)
from aerona.constants.api import IMAGE_UPLOAD_MAX_BYTES, PACKAGE_MEDIA_TYPE
from aerona.constants.http import LIBRARY_PATH
from aerona.constants.library import LIBRARY_PAGE_DEFAULT, LIBRARY_PAGE_MAX, UNIVERSE_ID_PATTERN, UNIVERSE_TAG_MAX_LENGTH
from aerona.constants.library_packages import LIBRARY_JOB_ID_PATTERN, TRASH_ENTRY_PATTERN
from aerona.constants.maintenance import PACKAGE_READ_BYTES
from aerona.constants.media import MEDIA_CHUNK_BYTES
from aerona.constants.timeouts import SSE_PING_SECONDS
from aerona.domain.enums.library import UniverseOrigin, UniverseSort, UniverseStatus
from aerona.domain.enums.library_jobs import LibraryJobKind, LibraryStreamKind
from aerona.domain.enums.meta import ImageMime
from aerona.services.library.catalogue import LibraryEventRecord, UniverseEdit, UniverseQuery, UniverseRecord
from aerona.services.library.feed import LibraryNotice
from aerona.services.library.jobs import LibraryJob
from aerona.services.library.service import LibraryService
from aerona.services.library.trash import TrashEntry

router = APIRouter(prefix=LIBRARY_PATH, tags=["library"])

COVER_TYPES = {".png": ImageMime.PNG.value, ".jpg": ImageMime.JPEG.value, ".webp": ImageMime.WEBP.value}
NO_STORE = "no-store"
SEARCH_MAX_LENGTH = 200
STREAM_DESCRIPTION = "Server-sent events, one LibraryStreamEvent per message."

UniverseId = Annotated[str, Path(pattern=UNIVERSE_ID_PATTERN)]
JobId = Annotated[str, Path(pattern=LIBRARY_JOB_ID_PATTERN)]
EntryId = Annotated[str, Path(pattern=TRASH_ENTRY_PATTERN)]


def get_library(request: Request) -> LibraryService:
    library: LibraryService = request.app.state.library
    return library


LibraryDep = Annotated[LibraryService, Depends(get_library)]


def universe_view(library: LibraryService, record: UniverseRecord) -> UniverseView:
    return UniverseView(
        id=record.id,
        name=record.name,
        summary=record.summary,
        notes=record.notes,
        status=record.status,
        pinned=record.pinned,
        origin=record.origin,
        origin_note=record.origin_note,
        tags=list(record.tags),
        created_at=record.created_at,
        opened_at=record.opened_at,
        updated_at=record.updated_at,
        epoch=record.epoch,
        year=record.year,
        population=record.population,
        sons=record.sons,
        size_bytes=record.size_bytes,
        schema_revision=record.schema_revision,
        app_version=record.app_version,
        cover_path=record.cover_path,
        media_prefix=record.media_prefix,
        is_open=library.hub.is_open(record.id),
        running_jobs=library.running_jobs(record.id),
    )


def event_view(event: LibraryEventRecord) -> LibraryEventView:
    return LibraryEventView(id=event.id, at=event.at, kind=event.kind, universe_id=event.universe_id, universe_name=event.universe_name, detail=event.detail)


def job_view(job: LibraryJob) -> LibraryJobView:
    preview = job.preview
    return LibraryJobView(
        id=job.id,
        kind=job.kind,
        status=job.status,
        stage=job.stage,
        universe_id=job.universe_id,
        universe_name=job.universe_name,
        progress=job.progress,
        done=job.done,
        total=job.total,
        error=job.error,
        notes=list(job.notes),
        file_name=job.file_name,
        size_bytes=job.size_bytes,
        preview=PackagePreviewView.model_validate({**preview.__dict__, "tags": list(preview.tags)}) if preview is not None else None,
    )


def trash_view(library: LibraryService, entry: TrashEntry) -> TrashEntryView:
    return TrashEntryView(
        id=entry.entry_id,
        universe_id=entry.manifest.id,
        name=entry.manifest.name,
        deleted_at=entry.deleted_at,
        purge_at=library.purge_at(entry),
        size_bytes=entry.size_bytes,
    )


@router.get("/universes", response_model=UniverseList)
async def list_universes(
    library: LibraryDep,
    *,
    q: Annotated[str, Query(max_length=SEARCH_MAX_LENGTH)] = "",
    status_filter: Annotated[UniverseStatus | None, Query(alias="status")] = None,
    include_archived: bool = False,
    origin: UniverseOrigin | None = None,
    tag: Annotated[str | None, Query(max_length=UNIVERSE_TAG_MAX_LENGTH)] = None,
    sort: UniverseSort = UniverseSort.OPENED,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=LIBRARY_PAGE_MAX)] = LIBRARY_PAGE_DEFAULT,
) -> UniverseList:
    chosen = status_filter if status_filter is not None else (None if include_archived else UniverseStatus.ACTIVE)
    page = await library.catalogue.page(UniverseQuery(text=q, status=chosen, origin=origin, tag=tag or None, sort=sort, offset=offset, limit=limit))
    facets = UniverseFacets(
        tags=[UniverseTagFacet(value=found, count=count) for found, count in await library.tag_counts()],
        origins=[UniverseOriginFacet(value=found, count=count) for found, count in page.origins.items()],
        statuses=[UniverseStatusFacet(value=found, count=count) for found, count in page.statuses.items()],
    )
    return UniverseList(items=[universe_view(library, record) for record in page.universes], total=page.total, offset=offset, limit=limit, facets=facets)


@router.post("/universes", response_model=UniverseView, status_code=status.HTTP_201_CREATED)
async def create_universe(body: UniverseCreate, library: LibraryDep) -> UniverseView:
    record = await library.create(body.name, body.notes, tuple(body.tags), body.summary)
    return universe_view(library, record)


@router.get("/universes/{universe_id}", response_model=UniverseDetail)
async def read_universe(universe_id: UniverseId, library: LibraryDep) -> UniverseDetail:
    record = await library.catalogue.require(universe_id)
    events = await library.recent_events(universe_id)
    return UniverseDetail(
        **universe_view(library, record).model_dump(),
        events=[event_view(event) for event in events],
    )


@router.patch("/universes/{universe_id}", response_model=UniverseView)
async def edit_universe(universe_id: UniverseId, body: UniversePatch, library: LibraryDep) -> UniverseView:
    change = UniverseEdit(name=body.name, notes=body.notes, summary=body.summary, tags=tuple(body.tags) if body.tags is not None else None, pinned=body.pinned)
    return universe_view(library, await library.edit(universe_id, change, body.status))


@router.post("/universes/{universe_id}/open", response_model=UniverseView)
async def open_universe(universe_id: UniverseId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.open(universe_id))


@router.post("/universes/{universe_id}/close", response_model=UniverseView)
async def close_universe(universe_id: UniverseId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.close(universe_id))


@router.post("/universes/{universe_id}/duplicate", response_model=UniverseView, status_code=status.HTTP_201_CREATED)
async def duplicate_universe(universe_id: UniverseId, body: UniverseDuplicate, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.duplicate(universe_id, body.name))


@router.post("/universes/{universe_id}/archive", response_model=UniverseView)
async def archive_universe(universe_id: UniverseId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.archive(universe_id))


@router.post("/universes/{universe_id}/restore", response_model=UniverseView)
async def restore_universe(universe_id: UniverseId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.restore(universe_id))


@router.delete("/universes/{universe_id}", response_model=TrashEntryView)
async def delete_universe(universe_id: UniverseId, library: LibraryDep) -> TrashEntryView:
    return trash_view(library, await library.delete(universe_id))


@router.get("/trash", response_model=TrashPageView)
async def list_trash(
    library: LibraryDep, offset: int = Query(default=0, ge=0), limit: int = Query(default=LIBRARY_PAGE_DEFAULT, ge=1, le=LIBRARY_PAGE_MAX)
) -> TrashPageView:
    entries, total, held = await library.trash(offset, limit)
    return TrashPageView(
        items=[trash_view(library, entry) for entry in entries],
        total=total,
        offset=offset,
        limit=limit,
        held_bytes=held,
        keep_days=library.settings.library_trash_days,
    )


@router.delete("/trash", response_model=TrashEmptied)
async def empty_trash(library: LibraryDep) -> TrashEmptied:
    return TrashEmptied(purged=await library.empty_trash())


@router.post("/trash/{entry_id}/restore", response_model=UniverseView)
async def recover_universe(entry_id: EntryId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.recover(entry_id))


@router.delete("/trash/{entry_id}", response_model=Done)
async def purge_universe(entry_id: EntryId, library: LibraryDep) -> Done:
    await library.purge(entry_id)
    return Done()


@router.post("/universes/{universe_id}/export", response_model=LibraryJobView, status_code=status.HTTP_202_ACCEPTED)
async def export_universe(universe_id: UniverseId, library: LibraryDep) -> LibraryJobView:
    return job_view(await library.export(universe_id))


@router.get("/exports/{job_id}", response_model=LibraryJobView)
async def read_export(job_id: JobId, library: LibraryDep) -> LibraryJobView:
    return job_view(library.jobs.get(job_id, LibraryJobKind.EXPORT))


async def file_chunks(path: FilePath) -> AsyncIterator[bytes]:
    with path.open("rb") as handle:
        while block := await asyncio.to_thread(handle.read, PACKAGE_READ_BYTES):
            yield block


@router.get("/exports/{job_id}/file", response_class=StreamingResponse, responses={200: {"content": {PACKAGE_MEDIA_TYPE: {}}}})
async def download_export(job_id: JobId, library: LibraryDep) -> StreamingResponse:
    job = library.export_file(job_id)
    assert job.file is not None
    headers = {"content-disposition": f"attachment; filename*=UTF-8''{quote(job.file_name)}", "content-length": str(job.size_bytes)}
    return StreamingResponse(file_chunks(job.file), media_type=PACKAGE_MEDIA_TYPE, headers=headers)


@router.delete("/exports/{job_id}", response_model=LibraryJobView)
async def discard_export(job_id: JobId, library: LibraryDep) -> LibraryJobView:
    return job_view(await library.cancel(job_id, LibraryJobKind.EXPORT))


@router.post("/imports", response_model=LibraryJobView, status_code=status.HTTP_202_ACCEPTED)
async def import_universe(library: LibraryDep, file: Annotated[UploadFile, File()]) -> LibraryJobView:
    async def chunks() -> AsyncIterator[bytes]:
        while block := await file.read(MEDIA_CHUNK_BYTES):
            yield block

    return job_view(await library.receive(chunks(), file.filename or ""))


@router.get("/imports/{job_id}", response_model=LibraryJobView)
async def read_import(job_id: JobId, library: LibraryDep) -> LibraryJobView:
    return job_view(library.jobs.get(job_id, LibraryJobKind.IMPORT))


@router.post("/imports/{job_id}/confirm", response_model=LibraryJobView, status_code=status.HTTP_202_ACCEPTED)
async def confirm_import(job_id: JobId, body: ImportConfirm, library: LibraryDep) -> LibraryJobView:
    return job_view(await library.confirm(job_id, body.name))


@router.delete("/imports/{job_id}", response_model=LibraryJobView)
async def cancel_import(job_id: JobId, library: LibraryDep) -> LibraryJobView:
    return job_view(await library.cancel(job_id, LibraryJobKind.IMPORT))


@router.get("/jobs", response_model=list[LibraryJobView])
async def list_jobs(library: LibraryDep) -> list[LibraryJobView]:
    return [job_view(job) for job in library.jobs.every()]


@router.put("/universes/{universe_id}/cover", response_model=UniverseView, operation_id="upload_library_cover")
async def upload_cover(universe_id: UniverseId, library: LibraryDep, file: Annotated[UploadFile, File()]) -> UniverseView:
    data = await file.read(IMAGE_UPLOAD_MAX_BYTES + 1)
    return universe_view(library, await library.set_cover(universe_id, data))


@router.put("/universes/{universe_id}/cover/from-media", response_model=UniverseView)
async def cover_from_media(universe_id: UniverseId, body: CoverFromMedia, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.cover_from_media(universe_id, body.file_name))


@router.get("/universes/{universe_id}/cover/paint", response_model=CoverPaintPrompt)
async def cover_paint_prompt(universe_id: UniverseId, library: LibraryDep) -> CoverPaintPrompt:
    return CoverPaintPrompt(prompt=await library.paint_prompt(universe_id))


@router.post("/universes/{universe_id}/cover/paint", response_class=Response, responses={200: {"content": {ImageMime.PNG.value: {}}}})
async def paint_cover(universe_id: UniverseId, body: CoverPaint, library: LibraryDep) -> Response:
    return Response(await library.paint_cover(universe_id, body.prompt), media_type=ImageMime.PNG.value, headers={"cache-control": NO_STORE})


@router.delete("/universes/{universe_id}/cover", response_model=UniverseView)
async def clear_cover(universe_id: UniverseId, library: LibraryDep) -> UniverseView:
    return universe_view(library, await library.clear_cover(universe_id))


@router.get("/universes/{universe_id}/cover", response_class=FileResponse, responses={200: {"content": {mime.value: {} for mime in ImageMime}}})
async def read_cover(universe_id: UniverseId, library: LibraryDep) -> FileResponse:
    found = await library.cover_file(universe_id)
    return FileResponse(found, media_type=COVER_TYPES.get(found.suffix.lower()), headers={"cache-control": NO_STORE})


@router.get("/events", response_model=LibraryEventPage)
async def library_events(
    library: LibraryDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIBRARY_PAGE_DEFAULT, ge=1, le=LIBRARY_PAGE_MAX),
    universe_id: str | None = Query(default=None, pattern=UNIVERSE_ID_PATTERN),
) -> LibraryEventPage:
    events, total = await library.catalogue.events(offset=offset, limit=limit, universe_id=universe_id)
    return LibraryEventPage(items=[event_view(event) for event in events], total=total, offset=offset, limit=limit)


async def stream_event(library: LibraryService, notice: LibraryNotice) -> LibraryStreamEvent:
    record = await library.catalogue.get(notice.universe_id) if notice.kind is LibraryStreamKind.UNIVERSE and notice.universe_id else None
    job = library.jobs.find(notice.job_id)
    return LibraryStreamEvent(
        id=notice.id,
        kind=notice.kind,
        at=notice.at,
        universe_id=notice.universe_id,
        universe=universe_view(library, record) if record is not None else None,
        job=job_view(job) if job is not None else None,
    )


@router.get("/events/stream", response_class=EventSourceResponse, responses={200: {"model": LibraryStreamEvent, "description": STREAM_DESCRIPTION}})
async def library_stream(library: LibraryDep) -> EventSourceResponse:
    async def generate() -> AsyncIterator[dict[str, str]]:
        hello = LibraryStreamEvent(id=library.feed.last_id, kind=LibraryStreamKind.HELLO, at=datetime.now(UTC), universe_id=None, universe=None, job=None)
        yield {"event": LibraryStreamKind.HELLO.value, "data": hello.model_dump_json()}
        async for notice in library.feed.subscribe():
            event = await stream_event(library, notice)
            yield {"id": str(notice.id), "event": notice.kind.value, "data": event.model_dump_json()}

    return EventSourceResponse(generate(), ping=SSE_PING_SECONDS)
