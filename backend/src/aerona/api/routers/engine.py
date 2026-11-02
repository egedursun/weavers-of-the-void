from fastapi import APIRouter

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.engine import EnginePhaseList, EnginePhaseView, IntegrityResult, IntegrityTaskList, IntegrityTaskView
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.events.kinds import EventKind
from aerona.services.engine_phases import list_phases
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


@router.post("/integrity/{task}", response_model=IntegrityResult)
async def run_integrity(task: IntegrityTask, services: ServicesDep) -> IntegrityResult:
    outcome = await run_task(services.database, task)
    if next(info for info in TASKS if info.task is task).changes_world:
        services.bus.publish(EventKind.WORLD_CHANGED, {"action": f"integrity:{task.value}"})
    return IntegrityResult(task=outcome.task, counters=outcome.counters, message=outcome.message)
