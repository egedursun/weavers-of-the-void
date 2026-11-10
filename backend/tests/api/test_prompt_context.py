import pytest

from aerona.prompts.catalog import PROMPTS
from aerona.services.prompt_preview.models import ContextBlockKind
from tests.api.conftest import ApiWorld, seeded

SON_BLOCKS = {ContextBlockKind.WORLD_SUMMARY, ContextBlockKind.SON_MEMORY, ContextBlockKind.POWERS}
ENTITY_BLOCKS = {ContextBlockKind.ENTITY_LINE, ContextBlockKind.ENTITY_DETAIL, ContextBlockKind.BOND_LINES, ContextBlockKind.MORTAL}


async def test_every_block_renders_for_a_seeded_world(api: ApiWorld) -> None:
    world = seeded(api)
    listing = (await api.http.get("/api/prompt-context/blocks")).json()
    assert {item["kind"] for item in listing} == {kind.value for kind in ContextBlockKind}
    for kind in ContextBlockKind:
        params: dict[str, int] = {}
        if kind in SON_BLOCKS:
            params["son_id"] = world.core.son.id
        if kind in ENTITY_BLOCKS:
            params["entity_id"] = world.creation.id
        response = await api.http.get(f"/api/prompt-context/{kind.value}", params=params)
        assert response.status_code == 200, (kind, response.text)
        body = response.json()
        assert body["characters"] == len(body["text"])
        assert body["token_estimate"] >= 0


async def test_block_arguments_are_validated(api: ApiWorld) -> None:
    assert (await api.http.get("/api/prompt-context/world-summary")).status_code == 400
    assert (await api.http.get("/api/prompt-context/entity-line")).status_code == 400
    assert (await api.http.get("/api/prompt-context/son-memory", params={"son_id": 999999})).status_code == 404
    assert (await api.http.get("/api/prompt-context/entity-line", params={"entity_id": 999999})).status_code == 404
    assert (await api.http.get("/api/prompt-context/world-line", params={"world_id": 999999})).status_code == 404
    assert (await api.http.get("/api/prompt-context/nonsense")).status_code in (400, 404, 422)


async def test_world_header_short_form_and_summary_section(api: ApiWorld) -> None:
    world = seeded(api)
    full = (await api.http.get("/api/prompt-context/world-header")).json()["text"]
    short = (await api.http.get("/api/prompt-context/world-header", params={"short": True})).json()["text"]
    assert full and short
    assert len(short) <= len(full)
    section = await api.http.get("/api/prompt-context/world-summary", params={"son_id": world.core.son.id, "section": "events"})
    assert section.status_code == 200


async def test_son_prompt_preview_reports_the_budget(api: ApiWorld) -> None:
    son = seeded(api).core.son
    body = (await api.http.get(f"/api/prompt-context/son-prompt/{son.id}")).json()
    assert body["son_name"] == son.name
    assert body["system_prompt"] and body["user_prompt"]
    assert body["total_characters"] == body["system_characters"] + body["user_characters"]
    assert body["token_estimate"] > 0
    assert body["over_limit"] == (body["total_characters"] > body["prompt_limit"])
    assert {section["section"] for section in body["summary_sections"]} >= {"header", "events", "geography"}
    assert body["paid_tools"] or body["free_tools"]
    assert (await api.http.get("/api/prompt-context/son-prompt/999999")).status_code == 404


async def test_prompt_catalogue_lists_prompts_and_tools(api: ApiWorld) -> None:
    body = (await api.http.get("/api/prompt-context/catalogue")).json()
    assert len(body["prompts"]) == len(PROMPTS)
    assert all(tool["description"] for tool in body["son_tools"])
    assert any(tool["read_only"] for tool in body["son_tools"])
    assert body["mortal_tools"]
    narrowed = (await api.http.get("/api/prompt-context/catalogue", params={"area": "fate"})).json()
    assert narrowed["prompts"] and all(item["area"] == "fate" for item in narrowed["prompts"])
    detail = (await api.http.get("/api/prompt-context/catalogue/fate_judgment_user")).json()
    assert detail["template_source"]
    assert detail["output_schema"]
    assert detail["variables"]
    plain = (await api.http.get("/api/prompt-context/catalogue/fate_judgment_system")).json()
    assert plain["output_schema"] is None
    assert (await api.http.get("/api/prompt-context/catalogue/nothing")).status_code in (400, 422)


async def test_tired_motif_override_cycle(api: ApiWorld) -> None:
    world = seeded(api)
    pinned = await api.http.put("/api/prompt-context/tired-motifs/overrides", json={"motif": "Rust", "mode": "pinned"})
    assert pinned.status_code == 200, pinned.text
    body = pinned.json()
    assert [item["key"] for item in body["motifs"]] == ["rust"]
    assert body["motifs"][0]["pinned"] is True
    assert body["overrides"][0]["mode"] == "pinned"
    listed = (await api.http.get("/api/prompt-context/tired-motifs")).json()
    assert listed["overrides"][0]["motif"] == "rust"
    scoped = await api.http.put("/api/prompt-context/tired-motifs/overrides", json={"motif": "salt", "mode": "allowed", "world_id": world.core.world.id})
    assert scoped.json()["overrides"][0]["world_id"] == world.core.world.id
    cleared = await api.http.post("/api/prompt-context/tired-motifs/overrides/clear", json={"motif": "rust"})
    assert cleared.json()["motifs"] == []
    assert cleared.json()["overrides"] == []
    assert (await api.http.put("/api/prompt-context/tired-motifs/overrides", json={"motif": "x", "mode": "pinned", "world_id": 999999})).status_code == 404
    assert (await api.http.put("/api/prompt-context/tired-motifs/overrides", json={"motif": "  ", "mode": "pinned"})).status_code == 400


@pytest.mark.parametrize("kind", [ContextBlockKind.CHRONICLER, ContextBlockKind.RECENT_EVENTS])
async def test_empty_world_blocks_do_not_fail(empty_api: ApiWorld, kind: ContextBlockKind) -> None:
    response = await empty_api.http.get(f"/api/prompt-context/{kind.value}")
    assert response.status_code in (200, 404, 409)
