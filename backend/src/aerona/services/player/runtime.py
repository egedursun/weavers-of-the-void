from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import BusyError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.job import JobKind
from aerona.engine.gods.essence import refund
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.player.guards import charge
from aerona.services.player.ports import CreativePorts
from aerona.services.player.scope import ActionOutcome, Effect, PlayerScope, perform

JobWork = Callable[[JobContext], Awaitable[dict[str, Any] | None]]


@dataclass
class PlayerRuntime:
    database: Database
    jobs: JobManager
    bus: EventBus
    ports: CreativePorts = field(default_factory=CreativePorts)
    llm_enabled: bool = True

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.bus.publish(kind, payload)

    def scope(self, session: AsyncSession, rules: Rules) -> PlayerScope:
        return PlayerScope(session, rules, self.publish)


@dataclass(frozen=True)
class CostedJob:
    action: str
    kind: ActionKind
    job_kind: JobKind
    lock: str
    cost: int
    rule_name: str
    target_node_id: int | None = None


def unavailable(what: str) -> ValidationFailedError:
    return ValidationFailedError(f"{what} needs the language model, which is disabled or not connected.")


async def _charge(runtime: PlayerRuntime, rules: Rules, job: CostedJob, command: BaseModel) -> ActionOutcome:
    async with runtime.database.write() as session:
        scope = runtime.scope(session, rules)

        async def body() -> Effect:
            creator = await scope.creator()
            spent = charge(creator, job.cost, job.rule_name)
            return Effect(f"{creator.name} paid {spent} essence: {job.action.replace('_', ' ')} began.", job.target_node_id, essence_spent=spent)

        return await perform(scope, job.action, job.kind, command, body)


async def refund_essence(runtime: PlayerRuntime, amount: int) -> None:
    if amount <= 0:
        return
    async with runtime.database.write() as session:
        refund(await CosmosRepository(session).require_creator(), amount)


async def submit_costed(runtime: PlayerRuntime, rules: Rules, job: CostedJob, command: BaseModel, work: JobWork) -> ActionOutcome:
    if runtime.jobs.busy_group(job.lock) is not None:
        raise BusyError(f"Busy: another {job.lock.replace('_', ' ')} is still in progress.")
    charged = await _charge(runtime, rules, job, command)

    async def handler(context: JobContext) -> dict[str, Any] | None:
        try:
            return await work(context)
        except BaseException:
            await refund_essence(runtime, charged.essence_spent)
            raise

    try:
        job_id = await runtime.jobs.submit(job.job_kind, handler, command.model_dump(mode="json"), exclusive_group=job.lock)
    except BaseException:
        await refund_essence(runtime, charged.essence_spent)
        raise
    return charged.model_copy(update={"values": {**charged.values, "job_id": job_id}})


@dataclass(frozen=True)
class FreeJob:
    action: str
    job_kind: JobKind
    lock: str


async def submit_free(runtime: PlayerRuntime, job: FreeJob, command: BaseModel, work: JobWork) -> ActionOutcome:
    if runtime.jobs.busy_group(job.lock) is not None:
        raise BusyError(f"Busy: {job.lock.replace('_', ' ')} is already being written.")
    job_id = await runtime.jobs.submit(job.job_kind, work, command.model_dump(mode="json"), exclusive_group=job.lock)
    return ActionOutcome(action=job.action, message="The work was queued.", values={"job_id": job_id})
