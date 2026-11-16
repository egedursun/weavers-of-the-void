from fastapi import APIRouter, Path
from fastapi.responses import FileResponse, StreamingResponse

from aerona.api.background import ensure_idle
from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.constants.api import PACKAGE_MEDIA_TYPE, SQLITE_MEDIA_TYPE
from aerona.constants.maintenance import BACKUP_SUFFIX, SAFE_FILE_NAME_PATTERN
from aerona.core.errors import NotFoundError
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.jobs.context import JOB_LABEL_KEY
from aerona.services.backups import BackupInfo, is_safe_file_name
from aerona.services.container import Services
from aerona.services.exchange import stream_and_delete

router = APIRouter(tags=["backups"])

NO_BACKUP = "No such backup."
RESTORED = "The world was restored from {name}; its previous state is in the safety backup {safety}."
RESET = "World deleted; its previous state is in the safety backup {safety}."


class RestoreRequest(RequestModel):
    file: str
    confirm: str


class ResetRequest(RequestModel):
    confirm: str


class SecondaryTarget(ApiModel):
    directory: str | None
    keep: int


class SecondaryTargetRequest(RequestModel):
    directory: str | None = None


class SafetyResult(ApiModel):
    ok: bool = True
    safety_backup: str


def backup_path(services: Services, name: str) -> str:
    if not is_safe_file_name(name) or not name.endswith(BACKUP_SUFFIX):
        raise NotFoundError(NO_BACKUP)
    path = services.application.backups.path_of(name)
    if not path.is_file():
        raise NotFoundError(NO_BACKUP)
    return str(path)


@router.get("/backups", response_model=list[BackupInfo])
async def list_backups(services: ServicesDep) -> list[BackupInfo]:
    return services.application.backups.backups()


@router.post("/backups", response_model=BackupInfo)
async def take_backup(services: ServicesDep) -> BackupInfo:
    context, log = await services.jobs.begin_external(JobKind.BACKUP, {JOB_LABEL_KEY: "taking a backup"})
    try:
        info = await services.application.backups.take()
    except Exception as error:
        await services.jobs.end_external(context, log, JobStatus.FAILED, error=str(error))
        raise
    await services.jobs.end_external(context, log, JobStatus.SUCCEEDED, {"file": info.file})
    return info


@router.get("/backups/secondary", response_model=SecondaryTarget)
async def secondary_target(services: ServicesDep) -> SecondaryTarget:
    backups = services.application.backups
    target = backups.secondary_target()
    return SecondaryTarget(directory=str(target) if target is not None else None, keep=services.rules.current.backup.secondary_target_backups)


@router.put("/backups/secondary", response_model=SecondaryTarget)
async def set_secondary_target(request: SecondaryTargetRequest, services: ServicesDep) -> SecondaryTarget:
    target = services.application.backups.set_secondary_target(request.directory)
    return SecondaryTarget(directory=str(target) if target is not None else None, keep=services.rules.current.backup.secondary_target_backups)


@router.post("/backups/restore", response_model=SafetyResult)
async def restore_backup(request: RestoreRequest, services: ServicesDep) -> SafetyResult:
    ensure_idle(services)
    application = services.application
    result = await application.backups.restore(request.file, request.confirm)
    await application.world_changed.fire(RESTORED.format(name=result.restored, safety=result.safety))
    return SafetyResult(safety_backup=result.safety)


@router.get("/backups/{file_name}/database", response_class=FileResponse)
async def download_backup(services: ServicesDep, file_name: str = Path(pattern=SAFE_FILE_NAME_PATTERN)) -> FileResponse:
    path = backup_path(services, file_name)
    return FileResponse(path, media_type=SQLITE_MEDIA_TYPE, filename=file_name)


@router.get("/backups/{file_name}/package", response_class=StreamingResponse)
async def download_package(services: ServicesDep, file_name: str = Path(pattern=SAFE_FILE_NAME_PATTERN)) -> StreamingResponse:
    backup_path(services, file_name)
    package = await services.application.exchange.export(images=True, backup_name=file_name)
    headers = {"content-disposition": f'attachment; filename="{package.file_name}"', "content-length": str(package.size)}
    return StreamingResponse(stream_and_delete(package.path), media_type=PACKAGE_MEDIA_TYPE, headers=headers)


@router.post("/world/reset", response_model=SafetyResult)
async def reset_world(request: ResetRequest, services: ServicesDep) -> SafetyResult:
    ensure_idle(services)
    application = services.application
    safety = await application.backups.reset(request.confirm)
    await application.world_changed.fire(RESET.format(safety=safety))
    return SafetyResult(safety_backup=safety)
