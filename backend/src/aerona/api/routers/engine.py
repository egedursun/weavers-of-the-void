from fastapi import APIRouter

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.engine import (
    EnginePhaseList,
    EnginePhaseView,
    IntegrityFindingList,
    IntegrityFindingView,
    IntegrityResult,
    IntegrityTaskList,
    IntegrityTaskView,
    ResolveFinding,
)
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.events.kinds import EventKind
from aerona.services.container import Services
from aerona.services.engine_phases import list_phases
from aerona.services.integrity.invariants import Finding, findings, resolve
from aerona.services.integrity.manual import TASKS, IntegrityTask, run_task

router = APIRouter(tags=["engine"])


SEED_STREAM_FORMAT = "world seed + epoch + '<phase>.<stream>'"


class EngineSeed(ApiModel):
    world_seed: int
    epoch: int
    stream_format: str
    phase_streams: list[str]


@router.get("/engine/phases", response_model=EnginePhaseList)
async def phases(services: ServicesDep) -> EnginePhaseList:
    async with reader(services) as session:
        rules = await world_rules(services, session)
    return EnginePhaseList(phases=[EnginePhaseView.model_validate(info) for info in list_phases(rules)])


@router.get("/engine/seed", response_model=EngineSeed)
async def engine_seed(services: ServicesDep) -> EngineSeed:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = await world_rules(services, session)
    return EngineSeed(
        world_seed=cosmos.rng_seed,
        epoch=cosmos.epoch,
        stream_format=SEED_STREAM_FORMAT,
        phase_streams=[info.name for info in list_phases(rules)],
    )


@router.get("/integrity/tasks", response_model=IntegrityTaskList)
async def integrity_tasks() -> IntegrityTaskList:
    return IntegrityTaskList(tasks=[IntegrityTaskView.model_validate(info) for info in TASKS])


@router.get("/integrity/findings", response_model=IntegrityFindingList)
async def integrity_findings(services: ServicesDep) -> IntegrityFindingList:
    async with reader(services) as session:
        found = await findings(session)
    return IntegrityFindingList(findings=[IntegrityFindingView.model_validate(item, from_attributes=True) for item in found])


@router.post("/integrity/findings/resolve", response_model=IntegrityFindingList)
async def resolve_finding(request: ResolveFinding, services: ServicesDep) -> IntegrityFindingList:
    current = [item for item in await integrity_findings_now(services) if same(item, request)]
    if not current:
        raise NotFoundError("That finding is already resolved.")
    async with services.database.write() as session:
        await resolve(session, current[0])
    services.bus.publish(EventKind.WORLD_CHANGED, {"action": "integrity:resolve"})
    return await integrity_findings(services)


async def integrity_findings_now(services: Services) -> list[Finding]:
    async with reader(services) as session:
        return await findings(session)


def same(item: Finding, request: ResolveFinding) -> bool:
    return (item.check, item.invariant, item.table, item.column, item.key) == (request.check, request.invariant, request.table, request.column, request.key)


@router.post("/integrity/{task}", response_model=IntegrityResult)
async def run_integrity(task: IntegrityTask, services: ServicesDep) -> IntegrityResult:
    outcome = await run_task(services.database, task)
    if next(info for info in TASKS if info.task is task).changes_world:
        services.bus.publish(EventKind.WORLD_CHANGED, {"action": f"integrity:{task.value}"})
    return IntegrityResult(task=outcome.task, counters=outcome.counters, message=outcome.message)
