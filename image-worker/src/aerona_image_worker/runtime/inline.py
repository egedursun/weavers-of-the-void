import asyncio

from aerona_image_worker.backends.base import BackendFactory, BackendSpec, ImageBackend
from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink
from aerona_image_worker.errors import GenerationFailedError, ImageTimeoutError, LoadTimeoutError


class InlineRunner:
    def __init__(self, spec: BackendSpec, factory: BackendFactory) -> None:
        self._spec = spec
        self._factory = factory
        self._backend: ImageBackend | None = None

    @property
    def loaded(self) -> bool:
        return self._backend is not None

    async def ensure_loaded(self, limit_seconds: float) -> None:
        if self._backend is not None:
            return
        backend = self._factory(self._spec)
        try:
            await asyncio.wait_for(asyncio.to_thread(backend.load), limit_seconds)
        except TimeoutError as error:
            raise LoadTimeoutError(f"model did not load within {limit_seconds:g}s") from error
        except Exception as error:
            raise GenerationFailedError(f"model failed to load: {type(error).__name__}: {error}") from error
        self._backend = backend

    async def generate(self, request: GenerationRequest, limit_seconds: float, report: ProgressSink) -> bytes:
        backend = self._backend
        if backend is None:
            raise GenerationFailedError("model is not loaded")
        loop = asyncio.get_running_loop()
        active = True

        def forward(kind: EventKind, step: int, total: int) -> None:
            if active:
                report(kind, step, total)

        def threadsafe(kind: EventKind, step: int, total: int) -> None:
            loop.call_soon_threadsafe(forward, kind, step, total)

        try:
            return await asyncio.wait_for(asyncio.to_thread(backend.generate, request, threadsafe), limit_seconds)
        except TimeoutError as error:
            self._backend = None
            raise ImageTimeoutError(f"image did not finish within {limit_seconds:g}s; the worker was restarted") from error
        except GenerationFailedError:
            raise
        except Exception as error:
            raise GenerationFailedError(f"{type(error).__name__}: {error}") from error
        finally:
            active = False

    async def unload(self) -> None:
        backend, self._backend = self._backend, None
        if backend is not None:
            await asyncio.to_thread(backend.unload)
