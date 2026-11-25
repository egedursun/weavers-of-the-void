import asyncio
import contextlib
import time
from dataclasses import dataclass, field

from aerona.agents.ports import LanguageModel
from aerona.db.migrations import upgrade_to_head
from aerona.db.session import Database
from aerona.engine.primitives.map_store import forget_database
from aerona.engine.startup import prepare_engine
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.services.agent_ports import player_creative_ports
from aerona.services.application import build_application, database_path, start_application, stop_application
from aerona.services.container import Services
from aerona.services.epoch_wiring import build_orchestrator, build_player
from aerona.services.integrity.data_repairs import checkpoint
from aerona.services.rules import RulesService
from aerona.settings import Settings

EPOCH_BUSY = "an epoch is running"
JOBS_BUSY = "jobs are running"
LISTENERS_BUSY = "someone is watching its live events"
REQUESTS_BUSY = "a request is being answered"


async def open_services(settings: Settings, model: LanguageModel | None, *, slots: asyncio.Semaphore | None = None) -> Services:
    database = Database(settings.database_url)
    bus = EventBus()
    jobs = JobManager(database, bus)
    await jobs.recover_interrupted()
    rules = RulesService(database)
    await rules.load()
    jobs.bind_capacity(lambda: rules.current.agents.concurrent_jobs)
    await prepare_engine(database)
    application = await build_application(settings, database, bus, rules, model=model, jobs=jobs)
    orchestrator = build_orchestrator(application, database, bus, jobs, rules, slots=slots)
    await orchestrator.recover()
    player = build_player(application, database, bus, jobs, player_creative_ports(application.agents))
    return Services(settings=settings, database=database, bus=bus, jobs=jobs, rules=rules, application=application, orchestrator=orchestrator, player=player)


async def close_services(services: Services) -> None:
    await stop_application(services.application)
    await services.jobs.shutdown()
    with contextlib.suppress(Exception):
        await asyncio.to_thread(checkpoint, database_path(services.database))
    await services.database.dispose()
    forget_database(services.database.engine.url)


async def launch_services(settings: Settings, model: LanguageModel | None, *, slots: asyncio.Semaphore | None = None) -> Services:
    settings.ensure_directories()
    await upgrade_to_head(settings.database_url)
    services = await open_services(settings, model, slots=slots)
    await start_application(services.application, services.database, services.jobs, services.rules, services.agents.llm_enabled)
    return services


@dataclass
class UniverseRuntime:
    universe_id: str
    services: Services
    opened: float = field(default_factory=time.monotonic)
    used: float = field(default_factory=time.monotonic)
    requests: int = 0

    def touch(self) -> None:
        self.used = time.monotonic()

    def busy_reason(self) -> str | None:
        jobs = self.services.jobs
        if jobs.busy_group(WORLD_GROUP) is not None:
            return EPOCH_BUSY
        if jobs.running_count > 0:
            return JOBS_BUSY
        if self.services.bus.subscriber_count > 0:
            return LISTENERS_BUSY
        if self.requests > 0:
            return REQUESTS_BUSY
        return None

    def idle_for(self) -> float:
        return time.monotonic() - self.used
