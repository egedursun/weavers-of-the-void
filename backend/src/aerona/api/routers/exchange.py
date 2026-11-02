from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from aerona.api.background import ensure_idle
from aerona.api.dependencies import ServicesDep
from aerona.constants.api import OCTET_STREAM, PACKAGE_MEDIA_TYPE
from aerona.services.exchange import ImportMode, ImportResult, stream_and_delete

router = APIRouter(tags=["exchange"])

CONFIRM_MAX_LENGTH = 20


@router.get("/world/export", response_class=StreamingResponse)
async def export_world(services: ServicesDep, images: bool = True) -> StreamingResponse:
    package = await services.application.exchange.export(images=images)
    headers = {"content-disposition": f'attachment; filename="{package.file_name}"', "content-length": str(package.size)}
    return StreamingResponse(stream_and_delete(package.path), media_type=PACKAGE_MEDIA_TYPE, headers=headers)


@router.post(
    "/world/import",
    response_model=ImportResult,
    openapi_extra={"requestBody": {"required": True, "content": {OCTET_STREAM: {"schema": {"type": "string", "format": "binary"}}}}},
)
async def import_world(
    request: Request,
    services: ServicesDep,
    mode: ImportMode = ImportMode.DISCOVERY,
    confirm: str | None = Query(default=None, max_length=CONFIRM_MAX_LENGTH),
) -> ImportResult:
    ensure_idle(services)
    data = await request.body()
    return await services.application.exchange.import_package(data, mode, confirm)
