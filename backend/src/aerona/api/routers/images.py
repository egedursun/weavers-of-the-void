from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from pydantic import Field

from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel, Done, JobAccepted, RequestModel
from aerona.api.schemas.records import EntitySummary, ImageRecord
from aerona.constants.api import IMMUTABLE_CACHE, MEDIA_PATH
from aerona.constants.maintenance import SAFE_FILE_NAME_PATTERN, SAFE_IMAGE_NAME_MAX_LENGTH
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.meta import ImageMime
from aerona.domain.enums.node import NodeKind
from aerona.jobs.context import JobContext
from aerona.services.images.media import StoredImage
from aerona.services.images.queue import BulkRun, ImageClass, QueuedImage, QueueStatus
from aerona.services.images.records import image_by_file_name, list_images, missing_count, missing_prompt_targets
from aerona.services.importance import missing_images

router = APIRouter(tags=["images"])

CAPTION_MAX_LENGTH = 120
COVER_TOOL = "image:cover"
CAPTION_TOOL = "image:caption"
DELETE_TOOL = "image:delete"
UPLOAD_TOOL = "image:upload"
PROMPTS_GROUP = "prompts"
UNSUPPORTED_TYPE = "Images must be PNG, JPEG or WEBP."
MISSING_IMAGE = "No such image file."
HEAD_METHOD = "HEAD"
NO_PROMPT_WRITER = "Image prompts need the language model, which is disabled or not connected."


class ImageListView(ApiModel):
    image: ImageRecord
    target_name: str | None
    target_kind: NodeKind | None
    target_world_id: int | None
    target_type: EntityType | None
    target_importance: int | None


class CaptionRequest(RequestModel):
    caption: str | None = Field(default=None, max_length=CAPTION_MAX_LENGTH)


class GenerateRequest(RequestModel):
    node_id: int = Field(ge=1)


class ImageGenStatus(ApiModel):
    status: QueueStatus
    missing: int


@router.head(f"{MEDIA_PATH}/{{file_name}}", include_in_schema=False)
@router.get(f"{MEDIA_PATH}/{{file_name}}", response_class=StreamingResponse, responses={status.HTTP_304_NOT_MODIFIED: {"description": "Not modified"}})
async def media(
    request: Request,
    services: ServicesDep,
    file_name: str = Path(pattern=SAFE_FILE_NAME_PATTERN, max_length=SAFE_IMAGE_NAME_MAX_LENGTH),
    w: int | None = Query(default=None, ge=1),
) -> Response:
    async with reader(services) as session:
        image = await image_by_file_name(session, file_name)
        if image is None:
            raise NotFoundError(MISSING_IMAGE)
        stored = StoredImage(object_key=image.object_key, content_type=image.mime.value, sha256=image.sha256, width=image.width)
    variant = await services.application.thumbnails.variant(stored, w)
    headers = {"cache-control": IMMUTABLE_CACHE, "x-content-type-options": "nosniff", "etag": variant.etag}
    if request.headers.get("if-none-match") == variant.etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    store = services.application.media
    if request.method == HEAD_METHOD:
        info = await store.head(variant.key)
        if info is None:
            raise NotFoundError(MISSING_IMAGE)
        return Response(headers={**headers, "content-length": str(info.size)}, media_type=variant.content_type)
    opened = await store.get(variant.key)
    if opened is None:
        raise NotFoundError(MISSING_IMAGE)
    headers["content-length"] = str(opened.info.size)
    return StreamingResponse(opened.chunks, media_type=variant.content_type, headers=headers)


@router.get("/images", response_model=list[ImageListView])
async def images(services: ServicesDep, node_id: int | None = Query(default=None, ge=1)) -> list[ImageListView]:
    async with reader(services) as session:
        items = await list_images(session, node_id)
    return [
        ImageListView(
            image=ImageRecord.model_validate(item.image),
            target_name=item.target_name,
            target_kind=item.target_kind,
            target_world_id=item.target_world_id,
            target_type=item.target_type,
            target_importance=item.target_importance,
        )
        for item in items
    ]


@router.post(
    "/images",
    response_model=ImageRecord,
    openapi_extra={"requestBody": {"required": True, "content": {mime.value: {"schema": {"type": "string", "format": "binary"}} for mime in ImageMime}}},
)
async def upload_image(
    request: Request, services: ServicesDep, node_id: int = Query(ge=1), caption: str | None = Query(default=None, max_length=CAPTION_MAX_LENGTH)
) -> ImageRecord:
    declared = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    try:
        mime = ImageMime(declared)
    except ValueError as error:
        raise ValidationFailedError(UNSUPPORTED_TYPE) from error
    data = await request.body()
    application = services.application
    async with services.database.write() as session, application.ledger.creator_action(session, UPLOAD_TOOL, ActionKind.EDIT_RECORD, {"node_id": node_id}):
        row = await application.image_records.upload(session, node_id, data, mime, caption)
        return ImageRecord.model_validate(row)


@router.put("/images/{image_id}/cover", response_model=ImageRecord)
async def set_cover(services: ServicesDep, image_id: int = Path(ge=1)) -> ImageRecord:
    application = services.application
    async with services.database.write() as session, application.ledger.creator_action(session, COVER_TOOL, ActionKind.EDIT_RECORD, {"image_id": image_id}):
        return ImageRecord.model_validate(await application.image_records.set_cover(session, image_id))


@router.put("/images/{image_id}/caption", response_model=ImageRecord)
async def set_caption(request: CaptionRequest, services: ServicesDep, image_id: int = Path(ge=1)) -> ImageRecord:
    application = services.application
    async with services.database.write() as session, application.ledger.creator_action(session, CAPTION_TOOL, ActionKind.EDIT_RECORD, {"image_id": image_id}):
        return ImageRecord.model_validate(await application.image_records.set_caption(session, image_id, request.caption))


@router.delete("/images/{image_id}", response_model=Done)
async def delete_image(services: ServicesDep, image_id: int = Path(ge=1)) -> Done:
    records = services.application.image_records
    async with services.database.write() as session:
        released = await records.delete(session, image_id)
    await records.release([released])
    return Done()


@router.get("/gallery/missing", response_model=list[EntitySummary])
async def gallery_missing(
    services: ServicesDep, limit: Annotated[int | None, Query(ge=1)] = None, entity_type: Annotated[EntityType | None, Query(alias="type")] = None
) -> list[EntitySummary]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        size = min(limit or rules.server.gallery_missing, rules.server.gallery_missing_max)
        return [EntitySummary.model_validate(row) for row in await missing_images(session, size, entity_type)]


@router.get("/image-gen", response_model=ImageGenStatus)
async def image_gen_status(services: ServicesDep) -> ImageGenStatus:
    async with reader(services) as session:
        missing = await missing_count(session)
    return ImageGenStatus(status=services.application.images.status(), missing=missing)


@router.post("/image-gen", response_model=QueuedImage, status_code=status.HTTP_202_ACCEPTED)
async def generate_image(request: GenerateRequest, services: ServicesDep) -> QueuedImage:
    return await services.application.images.enqueue(request.node_id, ImageClass.MANUAL)


@router.post("/image-gen/batch/start", response_model=BulkRun)
async def start_batch(services: ServicesDep) -> BulkRun:
    return await services.application.images.start_bulk()


@router.post("/image-gen/batch/stop", response_model=BulkRun)
async def stop_batch(services: ServicesDep) -> BulkRun:
    return services.application.images.stop_bulk()


@router.post("/entities/prompts/write-missing", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def write_missing_prompts(services: ServicesDep) -> JobAccepted:
    require_llm(services, "Writing image prompts")
    writer = services.application.ports.prompts
    if writer is None:
        raise ConflictError(NO_PROMPT_WRITER)

    async def work(context: JobContext) -> dict[str, Any]:
        rules = services.rules.current
        written = 0
        for round_number in range(rules.agents.prompt_batches):
            context.report(round_number / rules.agents.prompt_batches, PROMPTS_GROUP)
            async with services.database.read() as session:
                targets = [target.node_id for target in await missing_prompt_targets(session, rules.content.image_prompt_batch)]
            if not targets:
                break
            count = await writer.write_batch(targets)
            written += count
            if count == 0:
                break
        return {"written": written}

    return await submit(services, JobKind.CONTENT, PROMPTS_GROUP, work, label="writing of image prompts")
