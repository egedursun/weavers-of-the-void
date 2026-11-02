import copy

from aerona.domain.enums.job import JobStatus
from aerona.prompts import PromptId, output_model
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import open_api
from tests.prompts.payloads import PAYLOADS

SON_NAMES = ("Ozzeh", "Varum", "Kessa")


def genesis_model() -> FakeModel:
    model = FakeModel()
    data = copy.deepcopy(PAYLOADS[PromptId.GENESIS_USER])
    data["sons"] = [{**data["sons"][index], "name": name} for index, name in enumerate(SON_NAMES)]
    genesis = output_model(PromptId.GENESIS_USER)
    model.script(genesis, genesis.model_validate(data))
    awakening = output_model(PromptId.AWAKEN_PEOPLES_USER)
    model.fallback[awakening] = lambda _prompt: awakening.model_validate(copy.deepcopy(PAYLOADS[PromptId.AWAKEN_PEOPLES_USER]))
    return model


async def test_genesis_epoch_reads_action_and_undo(settings: Settings) -> None:
    model = genesis_model()
    async for api in open_api(settings, model=model, seeded=False):
        http = api.http
        started = await http.post("/api/genesis", json={"creator_name": "Aeron", "seed": "a salt lake under a white moon"})
        assert started.status_code == 202, started.text
        genesis = await api.wait_job(started.json()["job_id"])
        assert genesis["status"] == JobStatus.SUCCEEDED.value, genesis
        state = (await http.get("/api/state")).json()
        assert [son["son"]["name"] for son in state["sons"]] == list(SON_NAMES)
        model.enabled = False
        epoch = await http.post("/api/epochs/current/complete")
        assert epoch.status_code == 202
        finished = await api.wait_job(epoch.json()["job_id"])
        assert finished["status"] == JobStatus.SUCCEEDED.value, finished
        after = (await http.get("/api/state")).json()
        assert after["world"]["epoch"] == state["world"]["epoch"] + 1
        chronicle = (await http.get("/api/chronicle")).json()
        assert chronicle["total"] > 0
        graph = (await http.get("/api/graph")).json()
        assert graph["node_total"] > len(SON_NAMES)
        world_id = after["world"]["primary_world_id"]
        world_map = (await http.get(f"/api/worlds/{world_id}/map")).json()
        assert world_map["geometry"]["cells"]["x"]
        essence = after["creator"]["essence"]
        action = await http.post("/api/cheats/essence", json={"amount": 25})
        assert action.status_code == 200, action.text
        assert (await http.get("/api/state")).json()["creator"]["essence"] == essence + 25
        undone = await http.post(f"/api/ledger/{action.json()['ledger_entry_id']}/undo")
        assert undone.status_code == 200, undone.text
        assert (await http.get("/api/state")).json()["creator"]["essence"] == essence
