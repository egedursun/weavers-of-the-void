from collections.abc import AsyncIterator
from typing import Any

import pytest

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.divine_will import CycleStatus
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, fund_creator, open_api
from tests.divine_will.scripted import ScriptedWill
from tests.polling import until

SETTLED = frozenset({CycleStatus.DONE, CycleStatus.FAILED, CycleStatus.CANCELLED, CycleStatus.AWAITING_CONFIRMATION})


@pytest.fixture
def will_model() -> ScriptedWill:
    return ScriptedWill()


@pytest.fixture
async def will(settings: Settings, will_model: ScriptedWill) -> AsyncIterator[ApiWorld]:
    async for opened in open_api(settings, model=will_model, seeded=True):
        await fund_creator(opened)
        await set_rules(opened, "model", retry_wait_1=0, retry_wait_2=0, retry_wait_3=0)
        yield opened


async def set_rules(api: ApiWorld, namespace: str, **values: float) -> None:
    async with api.services.database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        snapshot = {name: dict(group) for name, group in cosmos.rules_snapshot.items()}
        snapshot.setdefault(namespace, {}).update({key: float(value) for key, value in values.items()})
        cosmos.rules_snapshot = snapshot


async def settled_cycle(api: ApiWorld, cycle_id: int) -> dict[str, Any]:
    bodies: list[dict[str, Any]] = []

    async def done() -> bool:
        bodies.append((await api.http.get(f"/api/divine-will/cycles/{cycle_id}")).json())
        return CycleStatus(bodies[-1]["status"]) in SETTLED and api.services.jobs.busy_group("divine_will") is None

    assert await until(done, step=0.02), bodies[-1] if bodies else cycle_id
    return bodies[-1]


async def ask(api: ApiWorld, text: str, mode: str = "command", attachment_ids: list[int] | None = None) -> dict[str, Any]:
    response = await api.http.post("/api/divine-will/cycles", json={"text": text, "mode": mode, "attachment_ids": attachment_ids or []})
    assert response.status_code == 202, response.text
    return await settled_cycle(api, response.json()["cycle_id"])
