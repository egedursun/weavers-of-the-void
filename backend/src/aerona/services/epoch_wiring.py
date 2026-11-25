import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.network_repair import network_rule_repair
from aerona.agents.runtime import AgentRuntime
from aerona.agents.turns.long_jobs import LongJobResult, resolve_orphaned_jobs
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.domain.enums.job import JobKind
from aerona.epoch.orchestrator import EpochOrchestrator
from aerona.epoch.ports import EpochHooks
from aerona.epoch.state import run_of
from aerona.events.bus import EventBus
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.application import ApplicationServices, epoch_end_maintenance, publish_changes
from aerona.services.notifications import prune_notifications
from aerona.services.player.assignments import auto_distribute
from aerona.services.player.ports import CreativePorts
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.player.scope import PlayerScope
from aerona.services.rules import RulesService

logger = logging.getLogger(__name__)

REFUNDED_NOTE = "{son}: the cost of the half-finished birth was refunded."
DISTRIBUTION_ACTION = "distribute_sons"

Work = Callable[[], Awaitable[object]]


@dataclass
class BackgroundPool:
    jobs: JobManager
    rules: RulesService
    pending: set[str] = field(default_factory=set)
    gate: asyncio.Semaphore | None = None
    tasks: set[asyncio.Task[Any]] = field(default_factory=set)
    active: int = 0

    @property
    def capacity(self) -> int:
        agents = self.rules.current.agents
        return max(1, agents.concurrent_jobs - agents.manual_job_share)

    def spare(self) -> int:
        return max(0, self.capacity - self.active)

    def _gate(self) -> asyncio.Semaphore:
        if self.gate is None:
            self.gate = asyncio.Semaphore(self.capacity)
        return self.gate

    def spawn(self, key: str, work: Work) -> bool:
        if key in self.pending or self.jobs.busy_group(key) is not None or self.jobs.kind_running(JobKind.GENESIS):
            return False
        self.pending.add(key)
        self.active += 1
        gate = self._gate()

        async def handler(context: JobContext) -> dict[str, Any]:
            try:
                async with gate:
                    context.report(0.0, key)
                    await work()
            finally:
                self.active -= 1
            return {"key": key}

        async def submit() -> None:
            try:
                await self.jobs.submit(JobKind.CONTENT, handler, {"key": key}, exclusive_group=key)
            except Exception:
                self.active -= 1
                logger.exception("background job %s could not start", key)
            finally:
                self.pending.discard(key)

        task = asyncio.create_task(submit())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return True


@dataclass(frozen=True)
class EpochWiring:
    application: ApplicationServices
    database: Database
    bus: EventBus
    jobs: JobManager
    rules: RulesService
    pool: BackgroundPool

    @property
    def runtime(self) -> AgentRuntime:
        return self.application.agents

    async def backup(self, label: str) -> str:
        return (await self.application.backups.take(label)).file

    async def complete_missing(self) -> None:
        async with self.database.write() as session:
            rules = await self.runtime.rules(session)
            epoch = (await CosmosRepository(session).require_cosmos()).epoch
            resolved = await resolve_orphaned_jobs(session, rules, epoch)
        for job in resolved:
            if job.result is LongJobResult.REFUNDED:
                self.runtime.note(REFUNDED_NOTE.format(son=job.son_name))
        if self.runtime.llm_enabled and self.application.completion.enabled():
            await self.application.completion.run()

    async def network_repair(self, epoch: int) -> None:
        await network_rule_repair(self.runtime, epoch)

    async def prune(self, session: AsyncSession, rules: Rules, epoch: int) -> None:
        await prune_notifications(session, rules)
        await self.application.ledger.prune(session, rules, epoch)

    async def after_tick(self, epoch: int, since_id: int) -> None:
        rules = await self.runtime.current_rules()
        async with self.database.write() as session:
            await self.application.chronicle.notify_unclassified(session, rules, since_id)
        publish_changes(self.bus, self.application.feed)

    async def after_epoch(self, epoch: int) -> None:
        rules = await self.runtime.current_rules()
        async with self.database.write() as session:
            run = await run_of(session, epoch)
            if run is not None and run.engine_since_chronicle_id is not None:
                await self.application.chronicle.notify_unclassified(session, rules, run.engine_since_chronicle_id)
        await epoch_end_maintenance(self.application, self.database, rules, epoch)
        publish_changes(self.bus, self.application.feed)

    async def image_autogen(self) -> None:
        await self.application.images.start_bulk(auto=True)

    async def distribute(self) -> int:
        async with self.database.write() as session:
            rules = await self.runtime.rules(session)
            scope = PlayerScope(session, rules, self.runtime.publish)
            return await auto_distribute(scope, await scope.context(DISTRIBUTION_ACTION))

    def hooks(self) -> EpochHooks:
        return EpochHooks(
            backup=self.backup,
            complete_missing=self.complete_missing,
            network_rule_repair=self.network_repair,
            prune=self.prune,
            after_epoch=self.after_epoch,
            image_autogen=self.image_autogen,
            spawn=self.pool.spawn,
            spare=self.pool.spare,
            distribute=self.distribute,
            after_tick=self.after_tick,
        )


def build_orchestrator(
    application: ApplicationServices, database: Database, bus: EventBus, jobs: JobManager, rules: RulesService, *, slots: asyncio.Semaphore | None = None
) -> EpochOrchestrator:
    wiring = EpochWiring(application, database, bus, jobs, rules, BackgroundPool(jobs, rules))
    return EpochOrchestrator(application.agents, jobs, wiring.hooks(), slots=slots)


def build_player(application: ApplicationServices, database: Database, bus: EventBus, jobs: JobManager, ports: CreativePorts) -> PlayerRuntime:
    return PlayerRuntime(database=database, jobs=jobs, bus=bus, ports=ports, llm_enabled=application.agents.llm_enabled)
