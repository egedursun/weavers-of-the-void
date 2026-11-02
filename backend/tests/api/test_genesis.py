from aerona.domain.enums.job import JobStatus
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, open_api
from tests.api.test_flow import genesis_model


async def test_wizard_lists_templates_and_options(empty_api: ApiWorld) -> None:
    body = (await empty_api.http.get("/api/genesis/wizard")).json()
    assert body["templates"]
    assert body["cosmos"]
    assert "english" in body["lore_languages"]


async def test_genesis_validates_and_needs_the_language_model(empty_api: ApiWorld) -> None:
    missing = await empty_api.http.post("/api/genesis", json={"creator_name": " ", "seed": "salt"})
    assert missing.status_code == 400
    offline = await empty_api.http.post("/api/genesis", json={"creator_name": "Aeron", "seed": "a salt lake"})
    assert offline.status_code == 409
    assert offline.json()["code"] == "conflict"


async def test_genesis_refuses_a_second_world(api: ApiWorld) -> None:
    response = await api.http.post("/api/genesis", json={"creator_name": "Aeron", "seed": "a salt lake"})
    assert response.status_code == 409


async def test_wizard_reports_first_son_limits(empty_api: ApiWorld) -> None:
    body = (await empty_api.http.get("/api/genesis/wizard")).json()
    options = body["first_sons"]
    assert options["minimum"] == 1
    assert options["maximum"] >= 3
    assert options["default"] == ["common", "rare", "legendary"]
    assert "mythic" not in options["rarities"]


async def test_genesis_validates_first_sons(empty_api: ApiWorld) -> None:
    body = {"creator_name": "Aeron", "seed": "salt"}
    assert (await empty_api.http.post("/api/genesis", json={**body, "first_sons": []})).status_code == 400
    assert (await empty_api.http.post("/api/genesis", json={**body, "first_sons": ["common"] * 7})).status_code == 400
    assert (await empty_api.http.post("/api/genesis", json={**body, "first_sons": ["mythic"]})).status_code == 400
    assert (await empty_api.http.post("/api/genesis", json={**body, "first_sons": ["common", "epic"]})).status_code == 409


async def test_genesis_creates_the_chosen_first_sons(settings: Settings) -> None:
    model = genesis_model()
    async for api in open_api(settings, model=model, seeded=False):
        started = await api.http.post(
            "/api/genesis", json={"creator_name": "Aeron", "seed": "a salt lake under a white moon", "first_sons": ["epic", "common"]}
        )
        assert started.status_code == 202, started.text
        job = await api.wait_job(started.json()["job_id"])
        assert job["status"] == JobStatus.SUCCEEDED.value, job
        state = (await api.http.get("/api/state")).json()
        assert sorted(son["son"]["rarity"] for son in state["sons"]) == ["common", "epic"]
        assert any("first 2 sons" in call.prompt and "Common, Epic" in call.prompt for call in model.calls)
