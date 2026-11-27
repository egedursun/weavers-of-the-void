from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Path, UploadFile, status
from fastapi.responses import Response

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.divine_will_attachments import (
    DivineWillAttachmentDetail,
    DivineWillAttachmentUpload,
    DivineWillAttachmentView,
    DivineWillIndexSource,
    DivineWillIndexView,
)
from aerona.constants.media import MEDIA_CHUNK_BYTES
from aerona.core.errors import NotFoundError
from aerona.db.tables.divine_will import DivineWillAttachmentRow
from aerona.domain.enums.divine_will import AttachmentKind
from aerona.media.store import read_all
from aerona.services.divine_will.attachments import MEGABYTE, AttachmentRefusedError, Upload, check_uploads, clean_name, store_uploads

router = APIRouter(prefix="/divine-will", tags=["divine_will"])

NO_ATTACHMENT = "No such attached file."
MISSING_FILE = "The attached file is missing from the media store."
INLINE = "inline"
DOWNLOAD = "attachment"


async def read_limited(upload: UploadFile, limit: int) -> bytes:
    parts: list[bytes] = []
    size = 0
    while block := await upload.read(MEDIA_CHUNK_BYTES):
        size += len(block)
        parts.append(block)
        if size > limit:
            break
    return b"".join(parts)


@router.post("/attachments", response_model=DivineWillAttachmentUpload, status_code=status.HTTP_201_CREATED)
async def upload_attachments(services: ServicesDep, files: Annotated[list[UploadFile], File()]) -> DivineWillAttachmentUpload:
    most, size = services.settings.divine_will_upload_max_files, services.settings.divine_will_upload_max_mb
    try:
        check_uploads([Upload(file.filename or "", file.content_type or "", b"") for file in files], most, size)
        uploads = [Upload(file.filename or "", file.content_type or "", await read_limited(file, size * MEGABYTE)) for file in files]
        check_uploads(uploads, most, size)
    except AttachmentRefusedError as refusal:
        raise HTTPException(refusal.status, refusal.message) from refusal
    rows = await store_uploads(services.database, services.application.media, uploads)
    services.application.lore_index.schedule_attachments()
    return DivineWillAttachmentUpload(attachments=[DivineWillAttachmentView.model_validate(row) for row in rows])


async def attachment_row(services: ServicesDep, attachment_id: int) -> DivineWillAttachmentRow:
    async with reader(services) as session:
        row = await session.get(DivineWillAttachmentRow, attachment_id)
    if row is None:
        raise NotFoundError(NO_ATTACHMENT)
    return row


@router.get("/attachments/{attachment_id}", response_model=DivineWillAttachmentDetail)
async def read_attachment(services: ServicesDep, attachment_id: int = Path(ge=1)) -> DivineWillAttachmentDetail:
    row = await attachment_row(services, attachment_id)
    data = await read_all(services.application.media, row.markdown_key) if row.markdown_key else None
    markdown = data.decode("utf-8", errors="replace") if data is not None else ""
    return DivineWillAttachmentDetail.model_validate({**DivineWillAttachmentView.model_validate(row).model_dump(), "markdown": markdown})


@router.get("/attachments/{attachment_id}/file", response_class=Response)
async def attachment_file(services: ServicesDep, attachment_id: int = Path(ge=1)) -> Response:
    row = await attachment_row(services, attachment_id)
    data = await read_all(services.application.media, row.media_key)
    if data is None:
        raise NotFoundError(MISSING_FILE)
    shown = INLINE if row.kind is AttachmentKind.IMAGE else DOWNLOAD
    name = clean_name(row.filename)
    headers = {
        "content-disposition": f"{shown}; filename*=UTF-8''{quote(name)}",
        "x-content-type-options": "nosniff",
        "content-security-policy": "sandbox",
    }
    return Response(content=data, media_type=row.mime, headers=headers)


@router.get("/index", response_model=DivineWillIndexView)
async def index_state(services: ServicesDep) -> DivineWillIndexView:
    state = services.application.lore_index.state()
    return DivineWillIndexView(
        status=state.status,
        note=state.note,
        semantic=state.semantic,
        passages=state.passages,
        embedded=state.embedded,
        pending=state.pending,
        share=state.share,
        sources=[DivineWillIndexSource(source=item.source, passages=item.passages, embedded=item.embedded) for item in state.sources],
        built_at=state.built_at,
        model=state.model,
    )
