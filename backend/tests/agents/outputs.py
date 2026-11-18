from aerona.prompts.schemas.fate import (
    ChronicleOutput,
    FactOutput,
    FateJudgmentOutput,
    FateWordOutput,
    NewThreadOutput,
    RewardOutput,
    VerdictDecision,
    VerdictOutput,
)
from aerona.prompts.schemas.shared import NamingItemOutput
from tests.agents.world import AgentWorld


def verdict(entity_id: int, decision: VerdictDecision, rationale: str = "It binds the salt to the stone.", fixed: str = "") -> VerdictOutput:
    return VerdictOutput(id=entity_id, decision=decision, rationale=rationale, fixed_description=fixed, motifs=["salt", "bone_wall"])


def naming(entity_id: int, name: str = "Teskaro") -> NamingItemOutput:
    return NamingItemOutput(
        id=entity_id,
        name=name,
        subtype="drought tale",
        description="A tale the river people tell of the year the water left. The children learn it before they learn to swim. It ends with a well.",
        image_prompt="A dry riverbed at dusk, cracked clay, a lone well, 35mm lens",
        motifs=["drought", "well"],
    )


def judgment(world: AgentWorld, decision: VerdictDecision = VerdictDecision.ACCEPT, fixed: str = "") -> FateJudgmentOutput:
    return FateJudgmentOutput(
        verdicts=[verdict(world.creation.id, decision, fixed=fixed)],
        namings=[naming(world.pending.id)],
        fulfilled_prophecies=[],
        closed_stories=[],
        advanced_stories=[],
        new_stories=[NewThreadOutput(text="The Orrin Folk want the river back.", related_ids=[world.creation.id])],
        rewards=[RewardOutput(son_id=world.core.son.id, fame=5, reason="He gave the salt a people.")],
        facts=[FactOutput(subject_id=world.creation.id, relation="is made of", object="salt and song")],
        words=[FateWordOutput(language_id=world.core.language.id, word="teska", meaning="drought", origin="the dry year")],
    )


def chronicle(name: str = "Age of Dry Wells") -> ChronicleOutput:
    return ChronicleOutput(
        age_name=name,
        narrative="Under the stone the diggers sang. The river left. A well was dug where the tale said it would be.",
        summary="The river people lost their river and dug a well that the drought tale had promised, and paid for it with a year of thirst.",
    )
