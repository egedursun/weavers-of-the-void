from fastapi import APIRouter, status

from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.jobs import JobResponse
from aerona.constants.http import JOBS_PATH
from aerona.constants.limits import JOB_HISTORY_PAGE_SIZE

router = APIRouter(prefix=JOBS_PATH, tags=["jobs"])


@router.get("", response_model=list[JobResponse])
async def list_jobs(services: ServicesDep, limit: int = JOB_HISTORY_PAGE_SIZE) -> list[JobResponse]:
    rows = await services.jobs.list_recent(min(limit, JOB_HISTORY_PAGE_SIZE))
    return [JobResponse.model_validate(row) for row in rows]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, services: ServicesDep) -> JobResponse:
    return JobResponse.model_validate(await services.jobs.get(job_id))


@router.post("/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_job(job_id: str, services: ServicesDep) -> None:
    await services.jobs.cancel(job_id)
