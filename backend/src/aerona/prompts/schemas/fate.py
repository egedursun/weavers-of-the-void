from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.entity import ProphecyReading
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.shared import MOTIFS, MOTIFS_MAX, MOTIFS_MIN, NamingItemOutput

FAME_MIN = 1


class VerdictDecision(StrEnum):
    ACCEPT = "accept"
    FIX = "fix"
    REJECT = "reject"


class VerdictOutput(OutputModel):
    id: int
    decision: VerdictDecision
    rationale: str = Field(description="{{ rationale_rule }}")
    fixed_description: str = Field(
        default="",
        description="MANDATORY if the decision is fix: the new description that removes the contradiction (if left empty the verdict counts as not given)",
    )
    motifs: list[str] = Field(min_length=MOTIFS_MIN, max_length=MOTIFS_MAX, description=MOTIFS)


class FulfilledProphecyOutput(OutputModel):
    id: int
    how: str
    reading: ProphecyReading = Field(
        description="true: as it was spoken; misread: it came true but not as everyone expected; self_fulfilling: it came true because people believed it"
    )


class ResolvedThreadOutput(OutputModel):
    id: int
    how: str = Field(description="How the story ended: 2 to 3 sentences, a concrete outcome")


class ClosedThreadOutput(OutputModel):
    id: int
    how: str = Field(description="How the story ended: 2 to 3 sentences, a concrete outcome and its cost, if any")


class AdvancedThreadOutput(OutputModel):
    id: int = Field(description="story")
    record_id: int = Field(description="This age's record that advanced the story (event, creation or named record)")
    how: str = Field(description="One sentence: how the story took a step")


class NewThreadOutput(OutputModel):
    text: str
    related_ids: list[int] = Field(default_factory=list)


class RewardOutput(OutputModel):
    son_id: int
    fame: int = Field(ge=FAME_MIN)
    reason: str = Field(
        description="Visible in the chronicle: one sentence in the world's lore language; do not write story or record numbers, mention the story by name"
    )


class FactOutput(OutputModel):
    subject_id: int
    relation: str = Field(description="Short predicate: the relation or property the fact states, in a few words")
    object_id: int | None = Field(default=None, description="if the object is an entity")
    object: str | None = Field(default=None, description="if the object is plain text")


class FateWordOutput(OutputModel):
    language_id: int
    word: str
    meaning: str
    origin: str = Field(description="Which event it was born from")


class FateJudgmentOutput(OutputModel):
    verdicts: list[VerdictOutput]
    namings: list[NamingItemOutput] = Field(description="For every pending record opened by the world engine")
    fulfilled_prophecies: list[FulfilledProphecyOutput]
    resolved_story: ResolvedThreadOutput | None = Field(
        default=None, description="The story among the priority candidates (stretched too long or stagnant) that resolved this age"
    )
    closed_stories: list[ClosedThreadOutput] = Field(description="Stories that close this age")
    advanced_stories: list[AdvancedThreadOutput] = Field(
        description="If an event or record of this age concretely advanced an open story even though nobody gave story_id"
    )
    new_stories: list[NewThreadOutput] = Field(description="New open stories born this age: whatever this age left unresolved or still unfolding")
    rewards: list[RewardOutput] = Field(description="Fame for sons who advanced open stories or visibly enriched the world")
    facts: list[FactOutput] = Field(
        description="MANDATORY. From every creation you accepted or fixed and every record you named, 1 to 3 short, definite facts: propositions about the thing itself that must not be violated in the future. Do not repeat recorded bonds like location, creator, language and patron; the engine writes those already"
    )
    words: list[FateWordOutput] = Field(description="New words that enter the languages from this age's events; must fit the language's sound system")


class ExtraJudgmentOutput(OutputModel):
    verdicts: list[VerdictOutput]


class ChroniclerIdentityOutput(OutputModel):
    name: str
    who: str = Field(description="Who they are: their name, their people, their trade and their link to the previous voice")


SUMMARY = "One but full sentence (at least {{ rules.fate.summary_min_chars }} characters): who, what, where, and its concrete consequence"


class WorldSectionOutput(OutputModel):
    world_id: int
    narrative: str = Field(description="1 to 2 paragraphs")
    summary: str = Field(description=SUMMARY)


class OutcomeClaimOutput(OutputModel):
    ref: str = Field(description="The fact sheet ref of a contest the text tells (war-…, conflict-…)")
    winner_id: int = Field(description="The id of the side the text presents as the winner")


class CreditClaimOutput(OutputModel):
    entity_id: int = Field(description="A record from the fact sheet whose making or blessing the text tells")
    actor_id: int = Field(description="The id of the god the text says did it (the creator's id or a son's id)")


class CountClaimOutput(OutputModel):
    ref: str = Field(description="The fact sheet ref the number is about")
    value: int = Field(description="The number the text states or implies for it")


class ChronicleCoverageOutput(OutputModel):
    covered: list[str] = Field(
        default_factory=list,
        description="The ref of EVERY fact sheet item (son, event, verdict, contest) the text tells, in the main narrative or a world section",
    )
    entity_ids: list[int] = Field(default_factory=list, description="The ids of the records from the fact sheet the text names")
    outcomes: list[OutcomeClaimOutput] = Field(default_factory=list, description="For every contest the text tells: whom it presents as the winner")
    credits: list[CreditClaimOutput] = Field(
        default_factory=list, description="For every record from the fact sheet whose maker the text names: whom it credits"
    )
    idle_actor_ids: list[int] = Field(
        default_factory=list, description="The ids of the gods the text presents as silent, idle or absent this age (empty if none)"
    )
    counts: list[CountClaimOutput] = Field(
        default_factory=list, description="Every number the text states about a fact sheet item (how many times, how many deeds); empty if none"
    )


class ChronicleOutput(OutputModel):
    age_name: str = Field(
        description="The mythic name to give this age, drawn from what most defined this age in this world; do NOT REPEAT the names or the shape of the names of previous ages"
    )
    narrative: str = Field(
        description="This age's narrative of 3 to 5 paragraphs in this world's own tone; from the mouth of a mortal chronicler, binding events together by cause and effect"
    )
    summary: str = Field(description=SUMMARY)
    chronicler: ChroniclerIdentityOutput = Field(description="The mortal chronicler who writes this age")
    worlds: list[WorldSectionOutput] | None = Field(
        default=None,
        description="A separate section for EACH world (all mandatory, each world once): what happened in that world this age; even if there were few events, how that world's age passed",
    )
    coverage: ChronicleCoverageOutput = Field(
        default_factory=ChronicleCoverageOutput, description="What the text covers, structured against the fact sheet (never shown to readers)"
    )


class ChronicleFixOutput(OutputModel):
    narrative: str = Field(description="The corrected main narrative (3 to 5 paragraphs)")
    worlds: list[WorldSectionOutput] | None = Field(default=None, description="Only the world sections that changed")
    coverage: ChronicleCoverageOutput = Field(
        default_factory=ChronicleCoverageOutput, description="What the corrected text covers, structured against the fact sheet"
    )


class WorldSectionsOutput(OutputModel):
    worlds: list[WorldSectionOutput] = Field(description="A separate section for each world (all required, each world once)")


class NamingsOutput(OutputModel):
    namings: list[NamingItemOutput] = Field(description="A naming for EVERY record below")
