from collections.abc import AsyncIterator
from typing import Any

import pytest

from aerona.domain.enums.presence import PresenceExchangeStatus
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, open_api
from tests.divine_will.conftest import set_rules
from tests.divine_will.scripted import ScriptedWill
from tests.polling import until

SETTLED = frozenset({PresenceExchangeStatus.DONE, PresenceExchangeStatus.FAILED, PresenceExchangeStatus.CANCELLED})


@pytest.fixture
def presence_model() -> ScriptedWill:
    return ScriptedWill()


@pytest.fixture
async def presence(settings: Settings, presence_model: ScriptedWill) -> AsyncIterator[ApiWorld]:
    async for opened in open_api(settings, model=presence_model, seeded=True):
        await set_rules(opened, "model", retry_wait_1=0, retry_wait_2=0, retry_wait_3=0)
        yield opened


async def summon(api: ApiWorld, node_id: int, guise: str = "creator", record: str = "on_record") -> dict[str, Any]:
    response = await api.http.post("/api/presence/sessions", json={"node_id": node_id, "guise": guise, "record": record})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def settled_exchange(api: ApiWorld, exchange_id: int) -> dict[str, Any]:
    bodies: list[dict[str, Any]] = []

    async def done() -> bool:
        bodies.append((await api.http.get(f"/api/presence/exchanges/{exchange_id}")).json())
        session_id = bodies[-1]["session_id"]
        return PresenceExchangeStatus(bodies[-1]["status"]) in SETTLED and api.services.jobs.busy_group(f"presence:{session_id}") is None

    assert await until(done, step=0.02), bodies[-1] if bodies else exchange_id
    return bodies[-1]


async def say(api: ApiWorld, session_id: int, text: str) -> dict[str, Any]:
    response = await api.http.post(f"/api/presence/sessions/{session_id}/exchanges", json={"text": text})
    assert response.status_code == 202, response.text
    return await settled_exchange(api, response.json()["exchange_id"])
