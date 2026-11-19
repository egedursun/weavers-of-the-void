import copy
import re
from pathlib import Path

from aerona.agents.grounding import GROUND_HEAD, GroundedModel
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.job import JobStatus
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.genesis import GenesisSettings
from aerona.prompts import PromptId, output_model
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import open_api, seeded
from tests.prompts.payloads import PAYLOADS
from tests.services.app.factories import make_son

SEED = "A present-day city where the old families keep secrets from the living."
SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


async def test_every_model_call_carries_the_players_seed_era_and_tone(settings: Settings) -> None:
    model = FakeModel()
    output = output_model(PromptId.COUNCIL_SESSION_USER)
    async for api in open_api(settings, model=model, seeded=True):
        assert isinstance(api.services.application.model, GroundedModel)
        assert api.services.application.agents.model is api.services.application.model
        async with api.services.database.write() as session:
            cosmos = await CosmosRepository(session).require_cosmos()
            cosmos.seed_idea = SEED
            cosmos.tone = "quiet, wry"
            cosmos.genesis_settings = GenesisSettings(magic=40, danger=30, peoples=1, technology=TechnologyEra.INFORMATION)
            await make_son(session, "Varum", seeded(api).core.world.id)
        son_id = seeded(api).core.son.id
        data = copy.deepcopy(PAYLOADS[PromptId.COUNCIL_SESSION_USER])
        data.update(speeches=[{"son_id": son_id, "words": "Peace."}], votes=[{"son_id": son_id, "vote": "yes", "reason": "Tired."}], alliances=[])
        model.script(output, output.model_validate(data))
        response = await api.http.post("/api/councils", json={"topic": "The harbour"})
        assert response.status_code == 202, response.text
        job = await api.wait_job(response.json()["job_id"])
        assert JobStatus(job["status"]) is JobStatus.SUCCEEDED
    assert model.calls
    for call in model.calls:
        assert call.system.startswith(GROUND_HEAD), call.label
        assert f"SEED: {SEED}" in call.system and "information age" in call.system and "TONE: quiet, wry" in call.system


def test_the_language_model_is_built_in_one_place_and_always_grounded() -> None:
    built = [path for path in SOURCE.rglob("*.py") if "LlmClient(" in path.read_text()]
    assert [path.name for path in built] == ["application.py"]
    text = (SOURCE / "services" / "application.py").read_text()
    assert re.search(r"GroundedModel\(\s*model or LlmClient\(", text)
