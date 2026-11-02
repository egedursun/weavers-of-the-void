import copy

from aerona.domain.enums.job import JobStatus
from aerona.prompts import PromptId, output_model
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import ApiWorld, open_api, seeded
from tests.prompts.payloads import PAYLOADS
from tests.services.app.factories import make_son


async def test_councils_list_and_need_the_language_model(api: ApiWorld) -> None:
    assert (await api.http.get("/api/councils")).json() == []
    assert (await api.http.post("/api/councils", json={"topic": "Shall the sea be bound?"})).status_code == 409
    assert (await api.http.post("/api/councils", json={"topic": ""})).status_code == 409
    assert (await api.http.post("/api/councils", json={})).status_code == 409


async def test_council_with_an_empty_agenda_lets_the_agent_pick_the_topic(settings: Settings) -> None:
    model = FakeModel()
    output = output_model(PromptId.COUNCIL_SESSION_USER)
    async for api in open_api(settings, model=model, seeded=True):
        son_id = seeded(api).core.son.id
        async with api.services.database.write() as session:
            second_id = (await make_son(session, "Varum", seeded(api).core.world.id)).id
        data = copy.deepcopy(PAYLOADS[PromptId.COUNCIL_SESSION_USER])
        data.update(
            speeches=[{"son_id": son_id, "words": "Peace."}],
            votes=[{"son_id": son_id, "vote": "yes", "reason": "Tired."}, {"son_id": second_id, "vote": "yes", "reason": "Agreed."}],
            alliances=[],
        )
        model.script(output, output.model_validate(data))
        response = await api.http.post("/api/councils", json={"topic": ""})
        assert response.status_code == 202, response.text
        job = await api.wait_job(response.json()["job_id"])
        assert JobStatus(job["status"]) is JobStatus.SUCCEEDED
        councils = (await api.http.get("/api/councils")).json()
        assert len(councils) == 1
        assert councils[0]["topic"].strip()
