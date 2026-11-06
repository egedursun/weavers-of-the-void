from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.world import Atmosphere, Gravity, StarType, WorldType
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.shared import PERCENT_MAX, NamingRuleOutput

ATTITUDE_LIMIT = 100


class PlacementChoice(StrEnum):
    EXISTING_STAR = "existing_star"
    NEW_STAR = "new_star"
    MOON = "moon"


class NativeKind(StrEnum):
    PEOPLE = "people"
    SPECIES = "species"


class NewStarOutput(OutputModel):
    name: str
    type: StarType = Field(description="The kind of sun; its kind sets how hot, bright, stable and unusual its worlds are: {{ star_types }}")
    description: str


class BirthRegionOutput(OutputModel):
    name: str
    subtype: str = Field(description="continent, inland sea, desert belt, archipelago, …")
    description: str = Field(description="2 to 4 sentences")
    danger: int = Field(ge=0, le=PERCENT_MAX)
    fertility: int = Field(ge=0, le=PERCENT_MAX)
    magic: int = Field(ge=0, le=PERCENT_MAX)
    water: bool = Field(default=False, description="True for a sea or ocean region that is water rather than land")
    image_prompt: str = Field(description="English image prompt. {{ image_prompt_rules }}")


class SkyBodyOutput(OutputModel):
    name: str
    subtype: str
    description: str
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class UniqueResourceOutput(OutputModel):
    name: str
    subtype: str
    description: str
    rule: str
    mechanics: list[ResourceMechanic] = Field(description="The rule's counterpart in the engine: {{ resource_mechanics }}")
    commodity: CommodityKind = Field(description="What its people draw from it when worked")
    material: MaterialKind | None = Field(default=None, description="The material it yields, for ore, stone or timber; null otherwise")
    region_index: int = Field(ge=0)
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class CosmicResourceOutput(OutputModel):
    name: str
    description: str
    rule: str = Field(description="How it is extracted, how it is used, what it makes possible")
    side_effect: str = Field(description="The price of long use: mutation, memory loss, the colour of the eyes…")
    region_index: int = Field(ge=0)
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class BirthWordOutput(OutputModel):
    word: str
    meaning: str
    kind: PartOfSpeech
    origin: str


class BirthLanguageOutput(OutputModel):
    name: str
    subtype: str
    description: str
    words: list[BirthWordOutput]


class OldGodOutput(OutputModel):
    name: str
    title: str
    domains: str = Field(description='Two domains, separated by "/"')
    description: str
    attitude: int = Field(ge=-ATTITUDE_LIMIT, le=ATTITUDE_LIMIT, description="Toward the newly arrived pantheon: -100 hostile, +100 friendly")
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class NativeOutput(OutputModel):
    kind: NativeKind
    name: str
    subtype: str
    description: str
    region_index: int = Field(ge=0)
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class NewWorldOutput(OutputModel):
    placement: PlacementChoice = Field(
        description="existing_star: a new planet orbiting a star in the list (most worlds are like this; choose this if the light the world wants is in the list); new_star: if a sun of a kind NOT in the list is needed, a distant system with its own sun (then the star field is mandatory); moon: the moon of an existing world"
    )
    type: WorldType = Field(description="The kind of world (a moon takes a world kind too): {{ world_types }}")
    dialect: NamingRuleOutput = Field(
        description="BUILD THIS FIRST: this world's own naming dialect, with vowels, consonants, syllable patterns and endings DIFFERENT from the main world. All names below (world, regions, sky, resource, natives) are derived with this dialect."
    )
    name: str = Field(description="The world's name; in the new dialect, repeating no existing name")
    language: BirthLanguageOutput = Field(description="This world's native language: matching the dialect exactly")
    description: str = Field(description="3 to 5 sentences: what makes this world distinctive and concrete")
    cosmology: str = Field(
        description="This world's OWN view of creation and death, 2 to 4 sentences; do not repeat the main cosmology, extend it with what is particular to this world"
    )
    gravity: Gravity
    atmosphere: Atmosphere
    time_factor: float = Field(
        description="Multiplier of years that pass in one age on this world ({{ '%g' | format(rules.world_physics.time_factor_min / 100) }} to {{ '%g' | format(rules.world_physics.time_factor_max / 100) }}). In the dream realm time stretches, in the realm of the dead it nearly stops."
    )
    day: str = Field(description="Its day, night and seasons in one sentence")
    star_id: int | None = Field(default=None, description="If existing_star, the id of the star it orbits")
    parent_world_id: int | None = Field(default=None, description="If moon, the id of the world it orbits")
    star: NewStarOutput | None = Field(
        default=None,
        description="MANDATORY if you chose new_star: the sun of the new system; its name cannot be the name of any star or world in the list. If left empty no new star is born, the world settles at an existing star.",
    )
    regions: list[BirthRegionOutput]
    sky: SkyBodyOutput = Field(description="The most prominent body in this world's sky (moon, ring, wound, second sun…)")
    unique_resource: UniqueResourceOutput = Field(
        description="A resource found only on this world; it should have a rule of its own (it decays, it is addictive, it can only be gathered in one season…)"
    )
    cosmic_resource: CosmicResourceOutput | None = Field(
        default=None,
        description="Fill ONLY if the cosmos has no travel resource yet: the single substance, unique to the cosmos, that makes travel between worlds (space folding) possible; long use carries a price of the world's own logic (an addiction, a change in the body or mind, a debt, a decay or another cost). It has a deposit on this world.",
    )
    old_god: OldGodOutput | None = Field(
        default=None,
        description="OPTIONAL: an old or foreign god who existed on this world before the pantheon, with worshippers of its own (not on every world; only if the world's logic requires it). It CANNOT be one of the cosmos's existing foreign gods: both its name and identity must be new.",
    )
    natives: list[NativeOutput] = Field(
        default_factory=list, description="Optional: living beings that existed on this world before the gods (a species or a people)"
    )
    image_prompt: str = Field(description="English image prompt: the whole world seen from orbit, with its star and sky. {{ image_prompt_rules }}")


class BondDirection(StrEnum):
    FROM_RECORD = "from_record"
    FROM_OTHER = "from_other"


class BondSuggestionOutput(OutputModel):
    record: str = Field(description="The RECORD's key exactly as shown (e.g. e12 or s3)")
    other: str = Field(description="The chosen candidate's key exactly as shown")
    direction: BondDirection
    type: BondKind
    reason: str
    shared_theme: bool = Field(default=False, description="True if the only link between the two is a shared theme, motif or image")


class BondSuggestOutput(OutputModel):
    bonds: list[BondSuggestionOutput]


class RelatedDecisionOutput(OutputModel):
    number: int = Field(description="The bond's number as shown (no N)")
    decision: str
    reason: str
    denies_bond: bool = Field(default=False, description="True if the reason says there is no real connection between the two")
    theme_only: bool = Field(
        default=False, description="True if the only thing the two share is a theme, motif, image, form or mood, with no act, place or person linking them"
    )


class BondNameRelatedOutput(OutputModel):
    decisions: list[RelatedDecisionOutput]
