from collections import Counter

from aerona.main import create_app
from aerona.services.player.catalog import ACTIONS
from aerona.settings import Settings
from tests.api.conftest import ApiWorld


def test_every_action_id_is_unique() -> None:
    counts = Counter(spec.id for spec in ACTIONS)
    assert [name for name, count in counts.items() if count > 1] == []


def test_every_api_schema_name_is_unique(settings: Settings) -> None:
    schemas = create_app(settings).openapi()["components"]["schemas"]
    assert [name for name in schemas if name.startswith("aerona__")] == []


async def test_a_son_s_divinity_reads_and_its_aims_and_wounds_are_set(api: ApiWorld) -> None:
    sons = (await api.http.get("/api/sons")).json()
    son_id = sons[0]["son"]["id"]
    set_aim = await api.http.post("/api/actions/god_goal:set", json={"god_id": son_id, "kind": "be_worshipped", "amount": 2})
    assert set_aim.status_code == 200, set_aim.text
    wound = await api.http.post("/api/actions/divine_wound:inflict", json={"god_id": son_id, "kind": "void_wound", "severity": 30})
    assert wound.status_code == 200, wound.text
    view = (await api.http.get(f"/api/gods/{son_id}/divinity")).json()
    assert [goal["kind"] for goal in view["goals"]] == ["be_worshipped"]
    assert [item["kind"] for item in view["wounds"]] == ["void_wound"]
    assert len(view["domains"]) == 2 and all(domain["hooks"] for domain in view["domains"])


async def test_the_creator_s_taboos_and_the_council_s_rulings_read_back(api: ApiWorld) -> None:
    taboo = await api.http.post("/api/actions/taboo:set", json={"act": "torture", "severity": 70})
    assert taboo.status_code == 200, taboo.text
    creator = (await api.http.get("/api/creator/divinity")).json()
    assert [row["act"] for row in creator["taboos"]] == ["torture"]
    decree = await api.http.post("/api/actions/ruling:decree", json={"motion": "cosmic_truce"})
    assert decree.status_code == 200, decree.text
    rulings = (await api.http.get("/api/council/rulings")).json()
    assert rulings["rulings"][0]["motion"] == "cosmic_truce" and rulings["rulings"][0]["active"]
    assert "none" not in rulings["motions"]
