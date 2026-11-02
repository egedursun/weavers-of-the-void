from aerona.prompts.schemas.fate import ChronicleOutput, FateJudgmentOutput, NamingsOutput
from aerona.prompts.schemas.narrative import VoicesOutput
from tests.agents.fakes import FakeModel, spoken
from tests.agents.outputs import chronicle, judgment
from tests.agents.world import AgentWorld


def script_full_epoch(model: FakeModel, world: AgentWorld) -> None:
    model.default_run = spoken("I watched the salt. «The wells remember us.»")
    model.fallback[NamingsOutput] = lambda _prompt: NamingsOutput(namings=[])
    model.fallback[FateJudgmentOutput] = lambda _prompt: judgment(world)
    model.fallback[ChronicleOutput] = lambda _prompt: chronicle()
    model.fallback[VoicesOutput] = lambda _prompt: VoicesOutput(views=[], beliefs=[])
