from typing import Any

from fastapi import APIRouter, status
from pydantic import Field
from sqlalchemy import select

from aerona.agents.council import convene_council
from aerona.api.background import require_llm
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.actions import ActionResponse
from aerona.api.schemas.common import RequestModel
from aerona.api.schemas.records import CouncilRecord
from aerona.db.tables.lore import CouncilRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import CouncilCaller
from aerona.domain.enums.job import JobKind
from aerona.jobs.context import JobContext
from aerona.services.player.runtime import CostedJob, submit_costed

router = APIRouter(tags=["council"])

TOPIC_MAX_LENGTH = 400
COUNCIL_LOCK = "council"
COUNCIL_RULE = "balance.council"


class CouncilRequest(RequestModel):
    topic: str = Field(default="", max_length=TOPIC_MAX_LENGTH)


@router.get("/councils", response_model=list[CouncilRecord])
async def list_councils(services: ServicesDep) -> list[CouncilRecord]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        rows = await session.scalars(select(CouncilRow).order_by(CouncilRow.id.desc()).limit(rules.server.council_minutes_list))
        return [CouncilRecord.model_validate(row) for row in rows]


@router.post("/councils", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def convene(request: CouncilRequest, services: ServicesDep) -> ActionResponse:
    require_llm(services, "A council of the gods")
    async with services.database.read() as session:
        rules = await world_rules(services, session)

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, COUNCIL_LOCK)
        result = await convene_council(services.agents, request.topic or None, CouncilCaller.CREATOR)
        return {"council_id": result.council_id, "passed": result.passed, "motion": result.motion}

    job = CostedJob("convene_council", ActionKind.CONVENE_COUNCIL, JobKind.CONTENT, COUNCIL_LOCK, rules.balance.council, COUNCIL_RULE)
    outcome = await submit_costed(services.player, rules, job, request, work)
    job_id = outcome.values.get("job_id")
    return ActionResponse(**outcome.model_dump(), job_id=str(job_id) if job_id is not None else None)
