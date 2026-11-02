import pytest

from tests.api.conftest import ApiWorld, seeded

STATIC_READS = (
    "/api/state",
    "/api/changes",
    "/api/catalogue",
    "/api/catalogue/enums",
    "/api/names",
    "/api/search?q=Harrow",
    "/api/genesis/wizard",
    "/api/epochs",
    "/api/epochs/current/estimate",
    "/api/stats/epochs",
    "/api/creator",
    "/api/creator/reputation",
    "/api/sons",
    "/api/sons/relations",
    "/api/entities",
    "/api/favorites",
    "/api/foreign-gods",
    "/api/cosmos",
    "/api/discovery-summary",
    "/api/map-notes",
    "/api/chronicle",
    "/api/chronicle/epochs",
    "/api/chronicle/perspectives",
    "/api/chronicle/cosmic",
    "/api/threads",
    "/api/codex.md",
    "/api/book",
    "/api/prayers",
    "/api/councils",
    "/api/graph",
    "/api/graph/health",
    "/api/languages",
    "/api/languages/tree",
    "/api/knowledge",
    "/api/images",
    "/api/gallery/missing",
    "/api/image-gen",
    "/api/batch-deepen",
    "/api/notifications",
    "/api/ledger",
    "/api/goals",
    "/api/opportunities",
    "/api/settings",
    "/api/backups",
    "/api/discovery",
    "/api/metrics/models",
    "/api/health/report",
    "/api/activity-log",
    "/api/actions",
    "/api/rules",
    "/api/jobs",
)


@pytest.mark.parametrize("path", STATIC_READS)
async def test_every_read_answers_on_a_living_world(api: ApiWorld, path: str) -> None:
    response = await api.http.get(path)
    assert response.status_code == 200, response.text


async def test_record_reads_answer_for_seeded_records(api: ApiWorld) -> None:
    world = seeded(api).core
    paths = (
        f"/api/sons/{world.son.id}",
        f"/api/sons/{world.son.id}/chat",
        f"/api/entities/{world.people.id}",
        f"/api/entities/{world.people.id}/bonds",
        f"/api/entities/{world.people.id}/chronicle",
        f"/api/worlds/{world.world.id}/guide",
        f"/api/worlds/{world.world.id}/map",
        f"/api/graph/path?a={world.son.id}&b={world.people.id}",
        f"/api/book?entity_id={world.people.id}",
    )
    for path in paths:
        response = await api.http.get(path)
        assert response.status_code == 200, f"{path}: {response.text}"


async def test_catalogue_serves_link_groups(api: ApiWorld) -> None:
    body = (await api.http.get("/api/catalogue")).json()
    groups = {group["key"]: group for group in body["link_groups"]}
    assert set(groups) == {"all", "travel", "no_location", "conflict", "faith", "lineage", "knowledge"}
    assert "enemy" in groups["conflict"]["kinds"]
    assert "route" in groups["travel"]["kinds"]
    assert "created" in groups["lineage"]["kinds"]
    assert "inside" in groups["all"]["kinds"]
    assert "inside" not in groups["no_location"]["kinds"]
    kinds = {kind["key"]: kind for kind in body["bond_kinds"]}
    assert kinds["trades_with"]["link_groups"] == ["all", "travel", "no_location", "knowledge"]
    assert kinds["worships"]["link_groups"] == ["all", "no_location", "faith"]
