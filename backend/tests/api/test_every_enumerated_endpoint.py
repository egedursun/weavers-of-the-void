from typing import Any

from httpx import AsyncClient

from aerona.domain.enums.entity import EntityType
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.military.records import KINDS
from aerona.prompts import PromptId
from aerona.services.prompt_preview.models import ContextBlockKind
from tests.api.test_every_endpoint import served
from tests.services.player.every_lever import pick

__all__ = ["served"]


async def answers(http: AsyncClient, urls: list[str], *, ok: bool) -> list[str]:
    broken = []
    for url in urls:
        response = await http.get(url)
        if response.status_code >= 500 or (ok and response.status_code != 200):
            broken.append(f"{url}: {response.status_code} {response.text[:200]}")
    return broken


async def test_every_prompt_mechanic_and_military_table_is_served(served: tuple[AsyncClient, Any]) -> None:
    http, _ = served
    urls = [f"/api/prompt-context/catalogue/{prompt.value}" for prompt in PromptId]
    urls += [f"/api/mechanics/{key}/links" for key in sorted(REGISTERED)]
    urls += [f"/api/military/records/{key}" for key in sorted(KINDS)]
    assert await answers(http, urls, ok=True) == []


async def test_every_context_block_renders_for_a_son_a_world_and_a_record(served: tuple[AsyncClient, Any]) -> None:
    http, services = served
    async with services.database.read() as session:
        son_id = await pick(session, "son", 0)
        world_id = await pick(session, "world", 0)
        entity_id = await pick(session, EntityType.MORTAL, 0)
    query = f"son_id={son_id}&world_id={world_id}&entity_id={entity_id}"
    urls = [f"/api/prompt-context/{kind.value}?{query}" for kind in ContextBlockKind]
    assert await answers(http, urls, ok=True) == []
