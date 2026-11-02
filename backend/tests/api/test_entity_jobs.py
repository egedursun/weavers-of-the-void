from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.job import JobStatus
from aerona.prompts import PromptId, output_model
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import ApiWorld, open_api, seeded


async def test_image_prompt_and_link_jobs_need_the_language_model(api: ApiWorld) -> None:
    entity_id = seeded(api).creation.id
    assert (await api.http.post(f"/api/entities/{entity_id}/image-prompt")).status_code == 409
    assert (await api.http.post(f"/api/entities/{entity_id}/suggest-links")).status_code == 409


async def test_entity_image_prompt_is_written_as_a_job(settings: Settings) -> None:
    model = FakeModel()
    output = output_model(PromptId.ENTITY_IMAGE_PROMPTS_USER)
    async for api in open_api(settings, model=model, seeded=True):
        entity_id = seeded(api).creation.id
        prompt = "A people of salt-diggers kneeling at a white quarry, painted in ochre and bone, wide dusk light."
        model.script(output, output.model_validate({"prompts": [{"id": entity_id, "prompt": prompt}]}))
        response = await api.http.post(f"/api/entities/{entity_id}/image-prompt")
        assert response.status_code == 202, response.text
        job = await api.wait_job(response.json()["job_id"])
        assert JobStatus(job["status"]) is JobStatus.SUCCEEDED
        assert job["result"]["written"] == 1
        async with api.services.database.read() as session:
            row = await session.get(EntityRow, entity_id)
            assert row is not None and row.image_prompt
        assert (await api.http.post("/api/entities/999999/image-prompt")).status_code == 404


async def test_suggest_links_runs_fate_over_one_record(settings: Settings) -> None:
    model = FakeModel()
    suggestion = output_model(PromptId.BOND_SUGGEST_USER)
    async for api in open_api(settings, model=model, seeded=True):
        entity_id = seeded(api).creation.id
        model.script(suggestion, suggestion.model_validate({"bonds": []}))
        response = await api.http.post(f"/api/entities/{entity_id}/suggest-links")
        assert response.status_code == 202, response.text
        job = await api.wait_job(response.json()["job_id"])
        assert JobStatus(job["status"]) is JobStatus.SUCCEEDED
        assert job["result"]["looked"] >= 1
        assert (await api.http.post("/api/entities/999999/suggest-links")).status_code == 404
