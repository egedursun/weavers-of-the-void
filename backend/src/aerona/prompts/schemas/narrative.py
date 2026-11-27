from pydantic import Field

from aerona.domain.enums.culture import SayingKind
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.kinds import KindConcept
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.shared import ExistenceOutput


class HistorianViewOutput(OutputModel):
    people_id: int
    text: str = Field(description="1 to 2 paragraphs; from this people's own side and interests")


class FolkBeliefOutput(OutputModel):
    people_id: int
    son_id: int = Field(description="0 for the creator god")
    name: str = Field(
        description="The name this people gave the god: if given in the prompt, EXACTLY that; if not, a new name with the sounds of the people's own language (NOT the god's name or title)"
    )
    story: str = Field(description="2 to 3 sentences: how this people tells of that god, by the name they gave the god")
    wrong: str = Field(description="One sentence: where their account really deviates, in the form of distortion given for that belief in the prompt.")


class VoicesOutput(OutputModel):
    views: list[HistorianViewOutput]
    beliefs: list[FolkBeliefOutput]


class SayingOutput(OutputModel):
    kind: SayingKind
    text: str


class DeepenedKind(OutputModel):
    concept: KindConcept = Field(description="What sort of thing it is")
    category: str = Field(description="Its category among those listed for its sort of thing: {{ kind_categories }}")
    name: str = Field(description="Its name, in the entity's own language")
    description: str = Field(description="1 to 2 sentences: what it is and how it is made or used")


class DeepenOutput(OutputModel):
    history: str = Field(description="The entity's history through the ages, 2 to 4 paragraphs")
    rumours: list[str] = Field(default_factory=list, description="Rumours circulating among mortals, true or false")
    sayings: list[SayingOutput] = Field(default_factory=list, description="Mortals' sayings about it; may contain words from the naming language")
    details: list[str] = Field(
        default_factory=list,
        description="Concrete details of its own, each of a different kind and specific to this entity; no two details of the same kind",
    )
    hidden_truth: str = Field(default="", description="Anything about it not yet known to anyone, if there is any; empty otherwise")
    special: dict[str, str] | None = None
    kinds: list[DeepenedKind] = Field(
        default_factory=list,
        description="Only for a people, a settlement, a realm, a faction or a cult: kinds of things it has come to make since it was last described; none otherwise",
    )


class EpicSectionOutput(OutputModel):
    title: str
    text: str = Field(description="2 to 4 paragraphs; based on the records, binding events by cause and effect")
    age_start: int
    age_end: int


class CreatorEpicOutput(OutputModel):
    title: str = Field(description="The epic's name")
    sections: list[EpicSectionOutput]
    line: str = Field(description="The single best-known line of the epic")


class GodNameOutput(OutputModel):
    name: str
    who: str = Field(description="Who uses this name")
    meaning: str


class CreatorDepthOutput(OutputModel):
    history: str = Field(description="How the god changed through the ages, 2 to 3 paragraphs")
    names: list[GodNameOutput]
    secrets: list[str] = Field(default_factory=list, description="Secrets even the god's own children do not know, if it keeps any")
    fears: list[str] = Field(default_factory=list, description="What the god fears, if anything")
    prohibitions: list[str] = Field(default_factory=list, description="Prohibitions the god set on creation, if any")
    gifts: list[str] = Field(default_factory=list, description="Gifts the god gave to mortals and to the god's children")
    desire: str = Field(description="What the god wants from creation")
    sayings: list[SayingOutput] = Field(default_factory=list)
    rumours: list[str] = Field(default_factory=list)
    hidden_truth: str = Field(default="", description="Anything about the god not yet known to anyone, if there is any; empty otherwise")


class ForeignPersonalityOutput(OutputModel):
    appearance: str = Field(description="Appearance; 1 to 2 sentences, concrete")
    temperament: str = Field(description="Temperament; 1 to 2 sentences, concrete")
    obsession: str = Field(description="What drives it most, if anything; 1 to 2 sentences, concrete")
    fear: str = Field(description="What it fears, if anything; 1 to 2 sentences, concrete")
    speech: str = Field(description="Speech; 1 to 2 sentences, concrete")
    secret: str = Field(description="Its secret, if it keeps one; 1 to 2 sentences, concrete")


class ForeignPowerOutput(OutputModel):
    name: str = Field(description="The power's name in its own world's language")
    effect: ForeignGodPowerEffect
    description: str = Field(description="1 to 2 sentences: how the power appears, how it works")


class ForeignGodDepthOutput(OutputModel):
    personality: ForeignPersonalityOutput
    existence: ExistenceOutput
    powers: list[ForeignPowerOutput] = Field(description="The god's powers; each has an effect in the engine: {{ foreign_god_powers }}")
    history: str = Field(description="Its history before and after the pantheon, 2 to 3 paragraphs; based on the records")
    names: list[GodNameOutput] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    sayings: list[SayingOutput] = Field(default_factory=list)
    rumours: list[str] = Field(default_factory=list)
    desire: str = Field(description="What it wants")
    view_of_pantheon: str = Field(default="", description="How it looks on the newly arrived pantheon and its sons; consistent with its attitude")
    worship: str = Field(default="", description="How its worshippers worship it")
    hidden_truth: str = Field(default="", description="Anything about it not yet known to anyone, if there is any; empty otherwise")
    image_prompt: str = Field(description="English portrait image prompt of this god. {{ image_prompt_rules }}")


class SonEpicOutput(OutputModel):
    title: str = Field(description="The epic's name")
    epic: str = Field(description="4 to 6 paragraphs, binding events by cause and effect")
    line: str = Field(description="The single best-known line of the epic")


class EntityImagePromptOutput(OutputModel):
    id: int
    prompt: str


class EntityImagePromptsOutput(OutputModel):
    prompts: list[EntityImagePromptOutput]


class CosmosImagePromptOutput(OutputModel):
    number: int
    prompt: str


class CosmosImagePromptsOutput(OutputModel):
    prompts: list[CosmosImagePromptOutput]
