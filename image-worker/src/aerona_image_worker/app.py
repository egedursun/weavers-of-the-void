import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from aerona_image_worker.api.routes import router
from aerona_image_worker.api.schemas import ErrorResponse
from aerona_image_worker.backends.factory import spec_from_settings
from aerona_image_worker.constants.defaults import SERVICE_NAME
from aerona_image_worker.errors import ImageNotReadyError, JobNotCancellableError, JobNotFoundError, WorkerError
from aerona_image_worker.jobs.scheduler import JobScheduler, SchedulerDefaults
from aerona_image_worker.runtime.base import Runner
from aerona_image_worker.runtime.factory import build_runner
from aerona_image_worker.settings import Settings, get_settings

ERROR_STATUSES: dict[type[WorkerError], int] = {
    JobNotFoundError: status.HTTP_404_NOT_FOUND,
    JobNotCancellableError: status.HTTP_409_CONFLICT,
    ImageNotReadyError: status.HTTP_409_CONFLICT,
}


def create_app(settings: Settings | None = None, runner: Runner | None = None) -> FastAPI:
    resolved = settings or get_settings()
    logging.basicConfig(level=resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        chosen = runner or build_runner(spec_from_settings(resolved), resolved.isolation)
        scheduler = JobScheduler(
            chosen,
            SchedulerDefaults(
                load_timeout_seconds=resolved.load_timeout_seconds,
                image_timeout_seconds=resolved.image_timeout_seconds,
                idle_unload_seconds=resolved.idle_unload_seconds,
                retained_jobs=resolved.retained_jobs,
            ),
        )
        app.state.settings = resolved
        app.state.scheduler = scheduler
        scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()

    app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)

    @app.exception_handler(WorkerError)
    async def handle_worker_error(_request: Request, error: WorkerError) -> JSONResponse:
        code = next((value for kind, value in ERROR_STATUSES.items() if isinstance(error, kind)), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(status_code=code, content=ErrorResponse(error=str(error)).model_dump())

    app.include_router(router)
    return app
