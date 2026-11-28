import pytest

from aerona.services import bulk_deepen
from tests.api.conftest import ApiWorld, seeded


async def test_state_without_a_world_is_empty(empty_api: ApiWorld) -> None:
    body = (await empty_api.http.get("/api/state")).json()
    assert body["world"] is None
    assert body["sons"] == []
    assert body["read_only"] is False
    assert body["llm_enabled"] is False


async def test_state_describes_the_living_world(api: ApiWorld) -> None:
    world = seeded(api).core
    body = (await api.http.get("/api/state")).json()
    assert body["world"]["name"] == world.cosmos.name
    assert body["creator"]["name"] == world.creator.name
    assert [son["son"]["id"] for son in body["sons"]] == [world.son.id]
    assert body["counts"]["people"] >= 1
    assert body["version"]


async def test_changes_falls_back_to_full_for_unknown_cursor_and_tracks_writes(api: ApiWorld) -> None:
    unknown = (await api.http.get("/api/changes", params={"since": "nope:1"})).json()
    assert unknown["full"] is True
    cursor = unknown["version"]
    world = seeded(api).core
    note = await api.http.put(f"/api/entities/{world.people.id}/favorite", json={"favorite": True})
    assert note.status_code == 200, note.text
    delta = (await api.http.get("/api/changes", params={"since": cursor})).json()
    assert delta["full"] is False
    assert world.people.id in [entity["id"] for entity in delta["entities"]]


async def test_state_reads_the_bulk_state_without_building_the_deepening_queue(api: ApiWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    seeded(api)

    async def refused(*_: object) -> list[object]:
        raise AssertionError("the state read built the whole deepening queue")

    monkeypatch.setattr(bulk_deepen, "deepening_queue", refused)
    reply = await api.http.get("/api/state")
    assert reply.status_code == 200, reply.text
    assert reply.json()["batch_deepen"]["running"] is False
