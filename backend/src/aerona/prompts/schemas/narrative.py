from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.shared import ExistenceOutput


class HistorianViewOutput(OutputModel):
    people_id: int
    historian: str = Field(description="The historian's name and title, in the people's language")
    text: str = Field(
        description="1 to 2 paragraphs; through this people's own eyes and interests: partial where its pride, grief or fear is at stake, silent on what it would rather forget"
    )


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


class SayingKind(StrEnum):
    PROVERB = "proverb"
    LULLABY = "lullaby"
    PRAYER = "prayer"
    MALEDICTION = "malediction"
    FOLK_SONG = "folk_song"
    OATH = "oath"
    TONGUE_TWISTER = "tongue_twister"
    HYMN = "hymn"


class SayingOutput(OutputModel):
    kind: SayingKind
    text: str


class DeepenOutput(OutputModel):
    history: str = Field(description="The entity's history through the ages, 2 to 4 paragraphs")
    rumours: list[str] = Field(default_factory=list, description="Rumours circulating among mortals, some true, some false")
    sayings: list[SayingOutput] = Field(default_factory=list, description="Mortals' sayings about it; may contain words from the naming language")
    details: list[str] = Field(
        default_factory=list,
        description="Concrete details of its own; each of a different kind (a habit, a material, a non-numeric measure, a ban, a sound, a texture, a colour…) and specific to this entity; never use the same sense twice",
    )
    hidden_truth: str = Field(default="", description="A truth nobody knows, connected to the entity's own history or to the laws of the world")
    special: dict[str, str] | None = None


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
    secrets: list[str] = Field(default_factory=list, description="Secrets even the god's own children do not know")
    fears: list[str] = Field(default_factory=list)
    prohibitions: list[str] = Field(description="Prohibitions the god set on creation and what happens when they are broken")
    gifts: list[str] = Field(default_factory=list, description="Gifts the god gave to mortals and to the god's children")
    desire: str = Field(description="What the god really wants from all of creation")
    sayings: list[SayingOutput] = Field(default_factory=list)
    rumours: list[str] = Field(default_factory=list)
    hidden_truth: str = Field(default="", description="The truth about the god that lies at the foundation of the cosmos")


class ForeignPersonalityOutput(OutputModel):
    appearance: str = Field(description="Appearance; 1 to 2 sentences, concrete")
    temperament: str = Field(description="Temperament; 1 to 2 sentences, concrete")
    obsession: str = Field(description="Obsession; 1 to 2 sentences, concrete")
    fear: str = Field(description="Fear; 1 to 2 sentences, concrete")
    speech: str = Field(description="Speech; 1 to 2 sentences, concrete")
    secret: str = Field(description="Its secret; 1 to 2 sentences, concrete")


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
    desire: str = Field(description="What it really wants")
    view_of_pantheon: str = Field(default="", description="How it looks on the newly arrived pantheon and its sons; consistent with its attitude")
    worship: str = Field(default="", description="How its worshippers worship it: rites, offerings, prohibitions")
    hidden_truth: str = Field(default="", description="The truth about it that nobody knows")
    image_prompt: str = Field(description="English portrait image prompt of this god. {{ image_prompt_rules }}")


class SonEpicOutput(OutputModel):
    title: str = Field(description="The epic's name")
    epic: str = Field(description="4 to 6 paragraphs; from the mouth of a mortal bard, binding events by cause and effect")
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
