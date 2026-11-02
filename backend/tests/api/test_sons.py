from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.son import SonDeathCause, SonStatus
from tests.api.conftest import ApiWorld, seeded
from tests.services.app.factories import bond


async def test_son_list_and_detail(api: ApiWorld) -> None:
    son = seeded(api).core.son
    listing = (await api.http.get("/api/sons")).json()
    assert listing[0]["son"]["name"] == son.name
    detail = (await api.http.get(f"/api/sons/{son.id}")).json()
    assert detail["son"]["id"] == son.id
    assert detail["kill_cost"] > 0
    assert isinstance(detail["bonds"], list)
    assert (await api.http.get("/api/sons/999999")).status_code == 404
    assert (await api.http.get("/api/sons/0")).status_code == 400


async def test_son_actions_record_ledger_entries(api: ApiWorld) -> None:
    son = seeded(api).core.son
    order = await api.http.put(f"/api/sons/{son.id}/order", json={"text": "Guard the salt road."})
    assert order.status_code == 200, order.text
    assert order.json()["ledger_entry_id"] is not None
    blessed = await api.http.post(f"/api/sons/{son.id}/bless", json={"kind": "hp"})
    assert blessed.status_code in (200, 400), blessed.text
    prompt = await api.http.put(f"/api/sons/{son.id}/image-prompt", json={"image_prompt": "A tall god of salt, painted in ochre."})
    assert prompt.status_code == 200, prompt.text
    missing = await api.http.post("/api/sons/999999/demote")
    assert missing.status_code == 404


async def test_essence_refusal_names_the_rule(api: ApiWorld) -> None:
    son = seeded(api).core.son
    async with api.services.database.write() as session:
        (await CosmosRepository(session).require_creator()).essence = 0
    response = await api.http.post(f"/api/sons/{son.id}/bless", json={"kind": "existence"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid"
    assert body["rule_key"] == "costs.bless_essence"
    assert body["rule_value"] > 0


async def test_llm_bound_son_endpoints_refuse_offline(api: ApiWorld) -> None:
    son = seeded(api).core.son
    assert (await api.http.post(f"/api/sons/{son.id}/chat", json={"text": "Speak."})).status_code == 409
    assert (await api.http.post(f"/api/sons/{son.id}/act")).status_code == 409
    assert (await api.http.post("/api/sons/summon", json={})).status_code in (400, 409)
    assert (await api.http.get(f"/api/sons/{son.id}/chat")).json() == []
    assert (await api.http.get("/api/sons/relations")).status_code == 200


async def test_dead_son_panel_reports_return_data(api: ApiWorld) -> None:
    world = seeded(api)
    son = world.core.son
    assert (await api.http.get(f"/api/sons/{son.id}/resurrection")).status_code == 409
    async with api.services.database.write() as session:
        await bond(session, world.core.people.id, son.id, BondKind.WORSHIPS)
        row = await session.get(SonRow, son.id)
        assert row is not None
        row.status = SonStatus.DEAD
        row.death_epoch = 1
        row.death_cause = SonDeathCause.KILLED_BY_CREATOR
    panel = (await api.http.get(f"/api/sons/{son.id}/resurrection")).json()
    minimum = api.services.rules.current.death.resurrection_min_epochs
    assert panel["son_id"] == son.id
    assert panel["earliest_return_epoch"] == 1 + minimum
    assert panel["devotion_required"] == api.services.rules.current.death.resurrection_devotion_required
    assert panel["devotion"] == 0
    assert world.core.people.id in [item["id"] for item in panel["loyal_communities"]]
    assert (await api.http.get("/api/sons/999999/resurrection")).status_code == 404


async def test_son_exposes_the_band_action_loss(api: ApiWorld) -> None:
    son = seeded(api).core.son
    rules = api.services.rules.current.core_rules
    healthy = (await api.http.get("/api/sons")).json()[0]
    assert healthy["band_action_loss"] == 0
    async with api.services.database.write() as session:
        row = await session.get(SonRow, son.id)
        assert row is not None
        row.existence = rules.existence_faded
    faded = (await api.http.get("/api/sons")).json()[0]
    assert faded["band"] == "faded"
    assert faded["band_action_loss"] == rules.faded_action_loss
    assert faded["band_effect"]
    assert faded["action_points"] == healthy["action_points"] - rules.faded_action_loss


async def test_turn_rank_is_exposed_on_the_son_record(api: ApiWorld) -> None:
    son = seeded(api).core.son
    assert (await api.http.get(f"/api/sons/{son.id}")).json()["son"]["turn_rank"] is None
    ranked = await api.http.post("/api/actions/son:turn_rank", json={"son_id": son.id, "rank": 2})
    assert ranked.status_code == 200, ranked.text
    assert (await api.http.get(f"/api/sons/{son.id}")).json()["son"]["turn_rank"] == 2
    cleared = await api.http.post("/api/actions/son:turn_rank", json={"son_id": son.id})
    assert cleared.status_code == 200, cleared.text
    assert (await api.http.get("/api/sons")).json()[0]["son"]["turn_rank"] is None
