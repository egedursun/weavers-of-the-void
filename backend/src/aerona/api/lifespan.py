import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from aerona.agents.ports import LanguageModel
from aerona.constants.api import LOCK_FILENAME
from aerona.core.errors import ConflictError
from aerona.core.logging import configure_logging
from aerona.db.migrations import upgrade_to_head
from aerona.db.session import Database
from aerona.engine.startup import prepare_engine
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.services.agent_ports import player_creative_ports
from aerona.services.application import build_application, database_path, start_application, stop_application
from aerona.services.container import Services
from aerona.services.epoch_wiring import build_orchestrator, build_player
from aerona.services.integrity.data_repairs import checkpoint
from aerona.services.rules import RulesService
from aerona.settings import Settings

logger = logging.getLogger(__name__)

ALREADY_RUNNING = "Weavers of the Void already runs on this world (process {pid}). Close the other process, or delete {lock} if it is stale."


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class InstanceLock:
    def __init__(self, directory: Path) -> None:
        self.path = directory / LOCK_FILENAME
        self.held = False

    def acquire(self) -> None:
        if self.path.exists():
            raw = self.path.read_text(encoding="utf-8").strip()
            other = int(raw) if raw.isdigit() else 0
            if other != os.getpid() and process_alive(other):
                raise ConflictError(ALREADY_RUNNING.format(pid=other, lock=LOCK_FILENAME))
        self.path.write_text(str(os.getpid()), encoding="utf-8")
        self.held = True

    def release(self) -> None:
        if not self.held:
            return
        with contextlib.suppress(OSError):
            raw = self.path.read_text(encoding="utf-8").strip()
            if raw == str(os.getpid()):
                self.path.unlink()
        self.held = False


async def open_services(settings: Settings, model: LanguageModel | None) -> Services:
    database = Database(settings.database_url)
    bus = EventBus()
    jobs = JobManager(database, bus)
    await jobs.recover_interrupted()
    rules = RulesService(database)
    await rules.load()
    jobs.bind_capacity(lambda: rules.current.agents.concurrent_jobs)
    await prepare_engine(database)
    application = await build_application(settings, database, bus, rules, model=model, jobs=jobs)
    orchestrator = build_orchestrator(application, database, bus, jobs, rules)
    await orchestrator.recover()
    player = build_player(application, database, bus, jobs, player_creative_ports(application.agents))
    return Services(settings=settings, database=database, bus=bus, jobs=jobs, rules=rules, application=application, orchestrator=orchestrator, player=player)


async def close_services(services: Services) -> None:
    await stop_application(services.application)
    await services.jobs.shutdown()
    with contextlib.suppress(Exception):
        await asyncio.to_thread(checkpoint, database_path(services.database))
    await services.database.dispose()


def lifespan_for(settings: Settings, model: LanguageModel | None = None) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings.ensure_directories()
        configure_logging(settings)
        lock = InstanceLock(settings.data_dir)
        lock.acquire()
        try:
            await upgrade_to_head(settings.database_url)
            services = await open_services(settings, model)
            app.state.services = services
            await start_application(services.application, services.database, services.jobs, services.rules, services.agents.llm_enabled)
            try:
                yield
            finally:
                await close_services(services)
        finally:
            lock.release()

    return lifespan
