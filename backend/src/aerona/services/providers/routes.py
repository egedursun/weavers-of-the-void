from functools import partial

from aerona.domain.enums.providers import ModelRole
from aerona.imaging.client import ProgressCallback
from aerona.imaging.contract import GeneratedImage, ImageJobRequest
from aerona.imaging.errors import ImageGenerationDisabledError, ImageWorkerError
from aerona.llm.errors import LlmUnavailableError
from aerona.llm.routes import ModelRoute
from aerona.services.providers.directory import ProviderDirectory
from aerona.services.providers.pool import BackendPool
from aerona.services.providers.records import ChainEntry

NO_IMAGE_MODEL = "No image model is set for this workspace or the server. Add one under Providers."


class UniverseRoutes:
    def __init__(self, directory: ProviderDirectory, pool: BackendPool, universe_id: str) -> None:
        self._directory = directory
        self._pool = pool
        self._universe_id = universe_id

    def entries(self, role: ModelRole) -> tuple[ChainEntry, ...]:
        return tuple(entry for entry in self._directory.chain(self._universe_id, role) if entry.usable and self._pool.unusable(entry.connection) is None)

    def routes(self, role: ModelRole) -> tuple[ModelRoute, ...]:
        return tuple(
            ModelRoute(entry.connection.label, entry.model, entry.sees_images, partial(self._pool.text, entry.connection)) for entry in self.entries(role)
        )


class ImageChain:
    def __init__(self, routes: UniverseRoutes, pool: BackendPool) -> None:
        self._routes = routes
        self._pool = pool

    @property
    def enabled(self) -> bool:
        return bool(self._routes.entries(ModelRole.IMAGES))

    def model_name(self) -> str:
        entries = self._routes.entries(ModelRole.IMAGES)
        if not entries:
            return ""
        first = entries[0]
        return f"{first.model} · {first.connection.label}" if first.model else first.connection.label

    async def aclose(self) -> None:
        return None

    async def generate(self, job: ImageJobRequest, on_progress: ProgressCallback | None = None) -> GeneratedImage:
        failure: ImageWorkerError = ImageGenerationDisabledError(NO_IMAGE_MODEL)
        for entry in self._routes.entries(ModelRole.IMAGES):
            try:
                provider = await self._pool.images(entry.connection, entry.model)
                return await provider.generate(job, on_progress)
            except LlmUnavailableError as error:
                failure = ImageGenerationDisabledError(str(error))
            except ImageWorkerError as error:
                failure = error
        raise failure
