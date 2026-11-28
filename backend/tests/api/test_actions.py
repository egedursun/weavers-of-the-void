import pytest

from aerona.api.routers import actions, languages, notes
from aerona.api.routers.actions import GENERIC_ACTIONS, TYPED_ROUTES
from aerona.events.kinds import EventKind
from aerona.main import create_app
from aerona.rules.registry import Rules
from aerona.services.player import catalog
from aerona.services.player.catalog import ACTIONS, ActionDescriptor
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, seeded


async def test_action_catalogue_lists_every_action_with_live_costs(api: ApiWorld) -> None:
    catalogue = (await api.http.get("/api/actions")).json()
    assert {item["id"] for item in catalogue} == {spec.id for spec in ACTIONS}
    summon = next(item for item in catalogue if item["id"] == "summon_son")
    assert str(api.services.rules.current.costs.summon_son) in summon["cost"]
    assert (summon["method"], summon["path"]) == ("POST", "/api/sons/summon")
    favorite = next(item for item in catalogue if item["id"] == "record:favorite")
    assert (favorite["method"], favorite["path"]) == ("PUT", "/api/entities/{entity_id}/favorite")
    shelter = next(item for item in catalogue if item["id"] == "settlement:shelter")
    assert shelter["path"] == "/api/actions/settlement:shelter"


async def test_action_catalogue_is_built_once_per_rules_and_follows_a_rule_change(api: ApiWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[Rules] = []
    describe = catalog.describe

    def counted(rules: Rules) -> list[ActionDescriptor]:
        built.append(rules)
        return describe(rules)

    monkeypatch.setattr(actions, "describe", counted)
    actions.CATALOGUES.clear()
    first = await api.http.get("/api/actions")
    second = await api.http.get("/api/actions")
    assert first.status_code == 200 and first.headers["content-type"].startswith("application/json")
    assert first.content == second.content
    assert len(built) == 1
    cost = api.services.rules.current.costs.summon_son
    changed = await api.http.put("/api/rules/costs/summon_son", json={"value": cost + 7})
    assert changed.status_code == 200, changed.text
    summon = next(item for item in (await api.http.get("/api/actions")).json() if item["id"] == "summon_son")
    assert str(cost + 7) in summon["cost"]
    assert len(built) == 2


async def test_generic_action_route_runs_ledgered_actions(api: ApiWorld) -> None:
    town = seeded(api).core.extra["town"].id
    response = await api.http.post("/api/actions/settlement:shelter", json={"settlement_id": town})
    assert response.status_code == 200, response.text
    assert response.json()["action"] == "settlement:shelter"
    missing_field = await api.http.post("/api/actions/settlement:shelter", json={"protected": True})
    assert missing_field.status_code == 400
    assert (await api.http.post("/api/actions/summon_son", json={})).status_code in (404, 405)


def test_openapi_exports_shared_enums_and_event_payloads(settings: Settings) -> None:
    schemas = create_app(settings).openapi()["components"]["schemas"]
    for name in ("EventKind", "JobStatus", "JobKind", "Rarity", "EntityType", "ChronicleKind", "ActionKind", "NodeKind", "ErrorCode"):
        assert name in schemas, name
    assert set(schemas["EventKind"]["enum"]) == {kind.value for kind in EventKind}
    assert "JobProgressEvent" in schemas
    assert "SettlementShelterInput" in schemas
    paths = create_app(settings).openapi()["paths"]
    generic = {path.removeprefix("/api/actions/") for path in paths if path.startswith("/api/actions/")}
    assert generic == {spec.id for spec in GENERIC_ACTIONS}
    assert not generic & set(TYPED_ROUTES)
    assert all(f"/api{alias.path}" in paths for alias in TYPED_ROUTES.values())


def test_every_typed_alias_replaces_its_generic_route(settings: Settings) -> None:
    paths = create_app(settings).openapi()["paths"]
    for alias in (*languages.ALIASES, *notes.ALIASES):
        assert alias.action_id in TYPED_ROUTES, alias.action_id
        assert f"/api/actions/{alias.action_id}" not in paths, alias.action_id
    assert "/api/languages/{language_id}/words" in paths
