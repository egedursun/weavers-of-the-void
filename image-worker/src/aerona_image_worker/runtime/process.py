import asyncio
import contextlib
import multiprocessing
import time
from multiprocessing.connection import Connection
from multiprocessing.context import SpawnProcess

from aerona_image_worker.backends.base import BackendSpec
from aerona_image_worker.constants.defaults import POLL_SLICE_SECONDS, SHUTDOWN_GRACE_SECONDS
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink
from aerona_image_worker.errors import BackendCrashedError, GenerationFailedError, ImageTimeoutError, LoadTimeoutError
from aerona_image_worker.runtime.child import serve
from aerona_image_worker.runtime.messages import ChildMessage, Failed, Finished, Generate, LoadFailed, Progress, Ready, Shutdown


class ProcessRunner:
    def __init__(self, spec: BackendSpec) -> None:
        self._spec = spec
        self._context = multiprocessing.get_context("spawn")
        self._process: SpawnProcess | None = None
        self._connection: Connection | None = None

    @property
    def loaded(self) -> bool:
        return self._process is not None and self._process.is_alive()

    async def ensure_loaded(self, limit_seconds: float) -> None:
        if self.loaded:
            return
        await self._terminate()
        parent, child = self._context.Pipe(duplex=True)
        process = self._context.Process(target=serve, args=(self._spec, child), daemon=True)
        process.start()
        child.close()
        self._process, self._connection = process, parent
        deadline = time.monotonic() + limit_seconds
        try:
            message = await self._receive(deadline)
        except TimeoutError as error:
            await self._terminate()
            raise LoadTimeoutError(f"model did not load within {limit_seconds:g}s") from error
        if isinstance(message, LoadFailed):
            await self._terminate()
            raise GenerationFailedError(f"model failed to load: {message.message}")
        if not isinstance(message, Ready):
            await self._terminate()
            raise BackendCrashedError("worker process sent an unexpected message while loading")

    async def generate(self, request: GenerationRequest, limit_seconds: float, report: ProgressSink) -> bytes:
        connection = self._connection
        if connection is None or not self.loaded:
            raise GenerationFailedError("model is not loaded")
        connection.send(Generate(request=request))
        deadline = time.monotonic() + limit_seconds
        while True:
            try:
                message = await self._receive(deadline)
            except TimeoutError as error:
                await self._terminate()
                raise ImageTimeoutError(f"image did not finish within {limit_seconds:g}s; the worker was restarted") from error
            if isinstance(message, Progress):
                report(message.kind, message.step, message.total)
            elif isinstance(message, Finished):
                return message.image
            elif isinstance(message, Failed):
                raise GenerationFailedError(message.message)
            else:
                await self._terminate()
                raise BackendCrashedError("worker process sent an unexpected message while generating")

    async def unload(self) -> None:
        connection, process = self._connection, self._process
        if connection is not None and process is not None and process.is_alive():
            with contextlib.suppress(OSError):
                connection.send(Shutdown())
            await asyncio.to_thread(process.join, SHUTDOWN_GRACE_SECONDS)
        await self._terminate()

    async def _receive(self, deadline: float) -> ChildMessage:
        connection, process = self._connection, self._process
        if connection is None or process is None:
            raise BackendCrashedError("worker process is not running")
        while not await asyncio.to_thread(connection.poll, min(POLL_SLICE_SECONDS, max(0.0, deadline - time.monotonic()))):
            if time.monotonic() >= deadline:
                raise TimeoutError
        try:
            message: ChildMessage = connection.recv()
        except (EOFError, OSError) as error:
            exit_code = process.exitcode
            await self._terminate()
            raise BackendCrashedError(f"worker process exited unexpectedly (exit code {exit_code})") from error
        return message

    async def _terminate(self) -> None:
        connection, process = self._connection, self._process
        self._connection, self._process = None, None
        if process is not None:
            if process.is_alive():
                process.kill()
            await asyncio.to_thread(process.join, SHUTDOWN_GRACE_SECONDS)
            if process.exitcode is not None:
                process.close()
        if connection is not None:
            connection.close()
