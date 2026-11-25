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
from aerona.services.library.adoption import prepare_library
from aerona.services.library.catalogue import Catalogue
from aerona.services.library.hub import UniverseHub
from aerona.services.library.service import LibraryService
from aerona.settings import Settings

logger = logging.getLogger(__name__)

ALREADY_RUNNING = "Weavers of the Void already runs on this library (process {pid}). Close the other process, or delete {lock} if it is stale."


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


def lifespan_for(settings: Settings, model: LanguageModel | None = None) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings.ensure_process_directories()
        configure_logging(settings)
        lock = InstanceLock(settings.process.root)
        lock.acquire()
        try:
            catalogue = Catalogue(settings.process)
            await prepare_library(catalogue)
            hub = UniverseHub(settings, catalogue, model)
            library = LibraryService(hub)
            app.state.hub = hub
            app.state.library = library
            await hub.start()
            await library.start()
            try:
                yield
            finally:
                await library.stop()
                await hub.stop()
                await catalogue.close()
        finally:
            lock.release()

    return lifespan
