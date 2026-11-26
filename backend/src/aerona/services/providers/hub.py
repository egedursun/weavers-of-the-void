from dataclasses import dataclass

from aerona.llm.tool_gate import ToolGate
from aerona.services.library.catalogue import Catalogue
from aerona.services.providers.directory import ProviderDirectory
from aerona.services.providers.legacy import adopt_legacy
from aerona.services.providers.login import LoginRunner
from aerona.services.providers.pool import BackendPool, base_environment
from aerona.services.providers.routes import ImageChain, UniverseRoutes
from aerona.services.providers.secrets import secret_box
from aerona.services.providers.service import ProviderService
from aerona.services.providers.store import ProviderStore
from aerona.settings import Settings


@dataclass
class Providers:
    directory: ProviderDirectory
    pool: BackendPool
    gate: ToolGate
    service: ProviderService
    claude_token: str
    worker_url: str

    async def adopt(self) -> None:
        if await adopt_legacy(self.service.store, self.service.box, self.claude_token, self.worker_url):
            await self.directory.refresh()

    def routes(self, universe_id: str) -> UniverseRoutes:
        return UniverseRoutes(self.directory, self.pool, universe_id)

    def images(self, universe_id: str) -> ImageChain:
        return ImageChain(self.routes(universe_id), self.pool)

    async def close(self) -> None:
        await self.service.logins.close()
        await self.pool.close()
        await self.gate.stop()


async def open_providers(settings: Settings, catalogue: Catalogue) -> Providers:
    process = settings.process
    box = secret_box(settings.secret_key.get_secret_value(), process.secret_key)
    store = ProviderStore(catalogue)
    directory = ProviderDirectory(store, box, process.provider_homes)
    gate = ToolGate()
    await gate.start()
    pool = BackendPool(settings.gateway_url, settings.agents_dir, gate)
    service: ProviderService | None = None

    async def finished(connection_id: int, secret: str) -> None:
        assert service is not None
        await service.logged_in(connection_id, secret)

    logins = LoginRunner(settings.agents_dir, base_environment, finished)
    service = ProviderService(store, directory, pool, box, logins)
    providers = Providers(directory, pool, gate, service, settings.claude_code_oauth_token.get_secret_value(), settings.image_worker_url)
    await directory.refresh()
    await providers.adopt()
    return providers
