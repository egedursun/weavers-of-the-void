import asyncio
from typing import Any

from aerona.core.errors import BusyError, ConflictError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.jobs.context import JobContext
from aerona.services.container import Services
from aerona.services.integrity.data_repairs import checkpoint
from aerona.services.maintenance.models import MaintenanceTask, TaskInfo, TaskResult
from aerona.services.maintenance.tasks import TASKS, TASKS_BY_ID, TaskEnvironment, TaskSpec

COMPLETION_GROUP = "completion"
MAINTENANCE_GROUP = "maintenance"
LLM_OFF = "{what} needs the language model, which is disabled or not connected."
EPOCH_BUSY = "An epoch is running; wait for it to finish or stop it."
BUSY = "Another maintenance task is already running."
NOTHING_MISSING = "Nothing is missing."


def group_of(task: MaintenanceTask) -> str:
    return COMPLETION_GROUP if task is MaintenanceTask.COMPLETION else MAINTENANCE_GROUP


def describe(services: Services) -> list[TaskInfo]:
    return [
        TaskInfo(
            task=spec.task,
            title=spec.title,
            description=spec.description,
            automatic=spec.automatic,
            rows=list(spec.rows),
            ledgered=spec.ledgered,
            needs_llm=spec.needs_llm,
            running=services.jobs.busy_group(group_of(spec.task)) is not None,
        )
        for spec in TASKS
    ]


def ensure_runnable(services: Services, spec: TaskSpec) -> None:
    if services.jobs.busy_group(group_of(spec.task)) is not None:
        raise BusyError(BUSY)
    if spec.task is not MaintenanceTask.COMPLETION and services.jobs.busy_group(WORLD_GROUP) is not None:
        raise BusyError(EPOCH_BUSY)
    if spec.needs_llm and not services.agents.llm_enabled:
        raise ConflictError(LLM_OFF.format(what=spec.title))


async def execute(services: Services, spec: TaskSpec, context: JobContext) -> TaskResult:
    application = services.application
    if spec.run is None:
        return TaskResult(task=spec.task, counters=await run_completion(services, context))
    entry_id: int | None = None
    async with services.database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = rules_from_snapshot(cosmos.rules_snapshot) if cosmos.rules_snapshot else services.rules.current
        env = TaskEnvironment(application, session, rules, cosmos.epoch, context.report)
        if spec.ledgered:
            async with application.ledger.creator_action(session, f"maintenance:{spec.task.value}", ActionKind.MAINTENANCE) as handle:
                counters = await spec.run(env)
            entry_id = handle.entry_id
        else:
            counters = await spec.run(env)
    if spec.task is MaintenanceTask.PRUNE:
        await asyncio.to_thread(checkpoint, application.backups.live_path)
    context.report(1.0, spec.title)
    return TaskResult(task=spec.task, counters=counters, ledger_entry_id=entry_id)


async def run_completion(services: Services, context: JobContext) -> dict[str, int]:
    report = await services.application.completion.run(context)
    return {"completed": len(report["completed"]), "failed": len(report["failed"])}


async def submit(services: Services, task: MaintenanceTask) -> str:
    spec = TASKS_BY_ID[task]
    ensure_runnable(services, spec)

    async def work(context: JobContext) -> dict[str, Any]:
        result = await execute(services, spec, context)
        return result.model_dump(mode="json")

    kind = JobKind.COMPLETION if task is MaintenanceTask.COMPLETION else JobKind.MAINTENANCE
    return await services.jobs.submit(kind, work, {"task": task.value}, exclusive_group=group_of(task))
