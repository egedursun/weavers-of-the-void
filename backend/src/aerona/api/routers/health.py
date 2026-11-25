from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from aerona.api.dependencies import HubDep, RuntimeDep, ServicesDep
from aerona.api.schemas.health import HealthReportResponse, HealthResponse
from aerona.constants.app import APP_VERSION
from aerona.constants.http import HEALTH_PATH
from aerona.domain.enums.meta import HealthStatus
from aerona.services.application import database_path
from aerona.services.metrics import health as health_report

router = APIRouter(tags=["system"])


@router.get(HEALTH_PATH, response_model=HealthResponse)
async def health(hub: HubDep, runtime: RuntimeDep) -> HealthResponse:
    if runtime is None:
        database_ok = await hub.catalogue.healthy()
        running = hub.running_jobs_total()
    else:
        async with runtime.services.database.read() as session:
            check = await session.execute(text("PRAGMA quick_check"))
            database_ok = check.scalar_one() == "ok"
        running = runtime.services.jobs.running_count
    settings = hub.settings
    return HealthResponse(
        status=HealthStatus.OK if database_ok else HealthStatus.DEGRADED,
        version=APP_VERSION,
        database_ok=database_ok,
        llm_enabled=settings.llm_enabled,
        claude_auth=settings.claude_auth,
        image_worker_configured=bool(settings.image_worker_url),
        running_jobs=running,
    )


@router.get(f"{HEALTH_PATH}/report", response_model=HealthReportResponse)
async def report(services: ServicesDep) -> HealthReportResponse:
    application = services.application
    latest = application.backups.latest()
    settings = services.settings
    found = health_report(
        rules=services.rules.current,
        ring=application.errors,
        database_path=database_path(services.database),
        log_file=settings.log_file.relative_to(settings.data_dir) if settings.log_file.is_relative_to(settings.data_dir) else Path(settings.log_file.name),
        latest_backup=(latest.file, latest.modified) if latest else None,
        backup_count=len(application.backups.backups()),
        running_jobs=services.jobs.running_count,
        read_only=application.discovery.active,
        uptime_seconds=application.metrics.uptime_seconds(),
    )
    return HealthReportResponse(report=found)
