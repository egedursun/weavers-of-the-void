from typing import Any

from fastapi import APIRouter, Path, status
from pydantic import BaseModel

from aerona.agents.chronicler import backfill_chronicles
from aerona.agents.image_prompter import missing_cosmos_prompts
from aerona.agents.summoner import complete_son_powers
from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep
from aerona.api.schemas.common import JobAccepted
from aerona.constants.maintenance import SAFE_FILE_NAME_PATTERN
from aerona.domain.enums.job import JobKind
from aerona.jobs.context import JobContext
from aerona.services.maintenance import runner
from aerona.services.maintenance.models import MaintenanceTask, TaskInfo

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class MissingContent(BaseModel):
    portrait: bool
    son_powers: list[int]
    sky_body: bool
    first_people: bool
    image_prompts: int
    undeepened_gods: list[int]
    pending_names: int
    past_narratives: list[int]
    anything_missing: bool


@router.get("/tasks", response_model=list[TaskInfo])
async def list_tasks(services: ServicesDep) -> list[TaskInfo]:
    return runner.describe(services)


@router.post("/tasks/{task}/run", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def run_task(services: ServicesDep, task: MaintenanceTask) -> JobAccepted:
    return JobAccepted(job_id=await runner.submit(services, task))


@router.get("/missing", response_model=MissingContent)
async def missing_content(services: ServicesDep) -> MissingContent:
    work = await services.application.completion.needed()
    return MissingContent(
        portrait=work.portrait,
        son_powers=work.son_powers,
        sky_body=work.sky_body,
        first_people=work.first_people,
        image_prompts=work.image_prompts,
        undeepened_gods=work.undeepened_gods,
        pending_names=work.pending_names,
        past_narratives=work.past_narratives,
        anything_missing=work.any,
    )


class BackupVerified(BaseModel):
    file: str
    ok: bool


@router.post("/backups/{file_name}/verify", response_model=BackupVerified)
async def verify_backup(services: ServicesDep, file_name: str = Path(pattern=SAFE_FILE_NAME_PATTERN)) -> BackupVerified:
    await services.application.backups.validate(file_name)
    return BackupVerified(file=file_name, ok=True)


@router.post("/sons/{son_id}/powers", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_powers(services: ServicesDep, son_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Writing a son's powers")

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "son powers")
        await complete_son_powers(services.agents, son_id)
        return {"son_id": son_id}

    return await submit(services, JobKind.CONTENT, f"son:{son_id}:powers", work, {"son_id": son_id})


@router.post("/cosmos-prompts", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def write_cosmos_prompts(services: ServicesDep) -> JobAccepted:
    require_llm(services, "Writing cosmos image prompts")

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "cosmos prompts")
        return {"written": await missing_cosmos_prompts(services.agents)}

    return await submit(services, JobKind.CONTENT, "cosmos:prompts", work)


@router.post("/chronicles", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def write_missing_chronicles(services: ServicesDep) -> JobAccepted:
    require_llm(services, "Writing missing chronicles")

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "missing chronicles")
        return {"written": await backfill_chronicles(services.agents)}

    return await submit(services, JobKind.CONTENT, "chronicle:backfill", work)
