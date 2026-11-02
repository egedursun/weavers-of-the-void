from collections.abc import Awaitable, Callable
from typing import Any

from aerona.api.schemas.common import JobAccepted
from aerona.core.errors import BusyError, ConflictError
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.context import JOB_LABEL_KEY, JobContext
from aerona.services.container import Services

LLM_OFF = "{what} needs the language model, which is disabled or not connected."
BUSY = "Busy: {what} is already running."
EPOCH_BUSY = "An epoch is running; wait for it to finish or stop it."
JOBS_BUSY = "Jobs are still running ({count}); wait for them or cancel them in the Jobs panel."
BULK_BUSY = "Batch deepening is running; stop it in Settings, Batch."
IMAGES_BUSY = "Image generation is running; stop it in the Image generation panel."

Work = Callable[[JobContext], Awaitable[dict[str, Any] | None]]


def require_llm(services: Services, what: str) -> None:
    if not services.agents.llm_enabled:
        raise ConflictError(LLM_OFF.format(what=what))


async def submit(services: Services, kind: JobKind, group: str, work: Work, params: dict[str, Any] | None = None, *, label: str | None = None) -> JobAccepted:
    if services.jobs.busy_group(group) is not None:
        raise BusyError(BUSY.format(what=label or group.replace("_", " ")))
    job_params = {**(params or {}), **({JOB_LABEL_KEY: label} if label else {})}
    job_id = await services.jobs.submit(kind, work, job_params, exclusive_group=group)
    return JobAccepted(job_id=job_id)


def ensure_idle(services: Services) -> None:
    if services.jobs.busy_group(WORLD_GROUP) is not None:
        raise BusyError(EPOCH_BUSY)
    if services.jobs.running_count:
        raise BusyError(JOBS_BUSY.format(count=services.jobs.running_count))
    application = services.application
    if application.bulk_deepen.state.running:
        raise BusyError(BULK_BUSY)
    if application.images.bulk.running:
        raise BusyError(IMAGES_BUSY)
