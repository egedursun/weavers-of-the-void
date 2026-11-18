from dataclasses import fields

from aerona.constants.llm import HAIKU_MODEL_ID
from aerona.llm.client import LlmClient
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import ApiWorld, open_api
from tests.polling import until

POLL_SECONDS = 0.02


async def test_engine_only_wiring_uses_a_disabled_haiku_client(empty_api: ApiWorld) -> None:
    services = empty_api.services
    model = services.application.model
    assert isinstance(model, LlmClient)
    assert model.model == HAIKU_MODEL_ID
    assert model.enabled is False
    assert services.agents.toolkits is not None
    hooks = services.orchestrator.hooks
    assert all(getattr(hooks, item.name) is not None for item in fields(hooks))
    ports = services.application.ports
    assert ports.genesis is None and ports.deepener is None
    assert services.player.ports.summoner is None
    assert services.player.llm_enabled is False


async def test_language_model_wiring_fills_every_port(settings: Settings) -> None:
    async for api in open_api(settings, model=FakeModel(), seeded=False):
        services = api.services
        lore = services.application.ports
        assert all(getattr(lore, item.name) is not None for item in fields(lore))
        creative = services.player.ports
        assert all(getattr(creative, item.name) is not None for item in fields(creative))
        assert services.agents.llm_enabled is True


async def test_background_pool_refuses_duplicate_keys(api: ApiWorld) -> None:
    hooks = api.services.orchestrator.hooks
    assert hooks.spawn is not None
    ran: list[str] = []

    async def work() -> None:
        ran.append("done")

    assert hooks.spawn("probe", work) is True
    assert hooks.spawn("probe", work) is False
    await until(lambda: bool(ran), step=POLL_SECONDS)
    await api.settle()
    assert ran == ["done"]


async def test_distribution_hook_counts_moves(api: ApiWorld) -> None:
    hooks = api.services.orchestrator.hooks
    assert hooks.distribute is not None
    assert await hooks.distribute() >= 0
