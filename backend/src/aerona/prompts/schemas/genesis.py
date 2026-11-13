from pydantic import Field

from aerona.constants.genesis import FIRST_SONS_CEILING
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import DimensionKind, WorldAge
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, ResourceMechanic
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.world import Atmosphere, ClimateEra, Gravity, StarType, WorldType
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.shared import (
    IMAGE_PROMPT,
    PERCENT_MAX,
    POWERS_PER_SON,
    CreatorGodOutput,
    ExistenceOutput,
    NamingRuleOutput,
    PowerOutput,
    SonProfileOutput,
    WordOutput,
)

SON_INDEX_MAX = FIRST_SONS_CEILING - 1
MOISTURE_MIN = -100


class GenesisRegionOutput(OutputModel):
    name: str
    subtype: str = Field(description="The kind of region in a few words, in this world's own terms")
    description: str = Field(description="3 to 5 sentences; refer to its neighbours")
    danger: int = Field(ge=0, le=PERCENT_MAX)
    fertility: int = Field(ge=0, le=PERCENT_MAX)
    magic: int = Field(ge=0, le=PERCENT_MAX)
    water: bool = Field(default=False, description="True for a sea or ocean region that is water rather than land")
    image_prompt: str = Field(description="English landscape image prompt. {{ image_prompt_rules }}")


class GenesisWorldOutput(OutputModel):
    type: WorldType = Field(description="The kind of the first world, as the seed calls for: {{ world_types }}")
    gravity: Gravity
    atmosphere: Atmosphere
    sea_pct: int = Field(ge=0, le=PERCENT_MAX, description="Share of the surface covered by water, 0 to 100")
    mountains_pct: int = Field(ge=0, le=PERCENT_MAX, description="Share of the land that is high ground, 0 to 100")
    moisture_pct: int = Field(ge=MOISTURE_MIN, le=PERCENT_MAX, description="How wet the land is, from -100 parched to 100 soaked")
    climate_era: ClimateEra = Field(description="The climate age the world begins in: {{ climate_eras }}")
    age: WorldAge = Field(description="How old the world already is when the first epoch begins: {{ world_ages }}")


class GenesisStarOutput(OutputModel):
    name: str = Field(description="The name of the sun the first world circles, in the naming language; not the world's own name")
    type: StarType = Field(description="The kind of sun; its kind sets how hot, bright, stable and unusual its world is: {{ star_types }}")
    description: str = Field(description="1 to 3 sentences about this sun")


class GenesisLayerOutput(OutputModel):
    name: str = Field(description="The name of the second layer of the cosmos, in the naming language")
    kind: DimensionKind = Field(description="What kind of layer it is: {{ dimension_kinds }}")
    description: str = Field(description="2 to 4 sentences: what this layer is and how it lies beside the first world")


class GenesisCosmicResourceOutput(OutputModel):
    name: str
    description: str
    rule: str = Field(description="How it is extracted, how it is used, what it makes possible")
    side_effect: str = Field(description="What long use does to those who use it, if anything; write none if it does nothing")
    region_index: int = Field(ge=0, description="Index into the regions list: where its first deposit lies")
    image_prompt: str = Field(description="English image prompt. {{ image_prompt_rules }}")


class FirstCelestialOutput(OutputModel):
    name: str
    subtype: str
    description: str
    domain: Domain
    image_prompt: str = Field(description="{{ image_prompt_rules }}")


class SonRelationOutput(OutputModel):
    i: int = Field(ge=0, le=SON_INDEX_MAX)
    j: int = Field(ge=0, le=SON_INDEX_MAX)
    value: int
    note: str


class GenesisOutput(OutputModel):
    world_name: str
    cosmology: str = Field(
        description="4 to 6 sentences: the shape of the universe, what it rests on, what lies above, below or beyond it, the flow of time, what death is"
    )
    naming: NamingRuleOutput = Field(description="The world's naming language as structured sound rules")
    tone: str = Field(description="The tone of the narrative, 2 sentences")
    god: CreatorGodOutput
    world: GenesisWorldOutput = Field(description="The first world itself: its kind, gravity, air, surface, climate age and age")
    star: GenesisStarOutput = Field(description="The sun the first world circles; the first world and its sun begin the cosmos as one system")
    regions: list[GenesisRegionOutput] = Field(
        description="The first regions the god founded by their own hand, neighbouring one another; land or water as the world's kind and the seed call for"
    )
    first_celestial: FirstCelestialOutput = Field(description="The most prominent body in the world's sky besides its sun, whatever that sky holds")
    cosmic_resource: GenesisCosmicResourceOutput = Field(
        description="The single substance, unique to the cosmos, that makes travel between worlds possible. It has one deposit in the region at region_index."
    )
    layer: GenesisLayerOutput | None = Field(
        default=None, description="Only for a layered cosmos: the second layer that lies beside the first world; leave empty otherwise"
    )
    sons: list[SonProfileOutput] = Field(min_length=1, max_length=FIRST_SONS_CEILING)
    relations: list[SonRelationOutput] = Field(description="Initial relations between the first sons; i and j are indices into the sons list, starting at 0")


class SonPowersOutput(OutputModel):
    powers: list[PowerOutput] = Field(min_length=POWERS_PER_SON, max_length=POWERS_PER_SON)
    existence: ExistenceOutput
    image_prompt: str = Field(
        description="English, detailed full-length portrait prompt: body, face, material, clothing, lighting, background, composition. {{ image_prompt_rules }}"
    )


class AwakenedRecord(OutputModel):
    name: str
    subtype: str
    description: str = Field(description="3 to 5 sentences")
    image_prompt: str = Field(description="English image prompt. {{ image_prompt_rules }}")


class AwakenedPeopleRecord(AwakenedRecord):
    population: int = Field(ge=0)
    martiality: int = Field(ge=0, le=PERCENT_MAX)
    craft: int = Field(ge=0, le=PERCENT_MAX)
    magic: int = Field(ge=0, le=PERCENT_MAX)


class AwakenedLanguage(AwakenedRecord):
    words: list[WordOutput]


class AwakenedSettlement(AwakenedRecord):
    population: int = Field(ge=0)


class AwakenedResource(AwakenedRecord):
    domain: Domain
    commodity: CommodityKind = Field(description="What the resource yields when worked")
    material: MaterialKind | None = Field(default=None, description="The material it yields, for ore, stone or timber; null otherwise")


class AwakenedKnowledge(AwakenedRecord):
    branch: KnowledgeBranch


class AwakenedPeople(OutputModel):
    region_id: int
    people: AwakenedPeopleRecord
    language: AwakenedLanguage
    settlement: AwakenedSettlement
    resource: AwakenedResource
    knowledge: AwakenedKnowledge
    tradition: AwakenedRecord
    worshipped_son_id: int = Field(description="The son they worship; 0 if none")


class AwakenPeoplesOutput(OutputModel):
    peoples: list[AwakenedPeople] = Field(min_length=1)


class RevelationLink(OutputModel):
    target_kind: str = Field(description="entity or son")
    target_id: int
    kind: BondKind
    description: str = ""


class RevelationOutput(OutputModel):
    type: EntityType
    name: str
    subtype: str
    description: str = Field(description="4 to 7 sentences; in the world's lore language, bound to existing things")
    domain: Domain
    power_level: int = Field(ge=1)
    location_id: int = Field(description="The id of a suitable location entity; 0 if location-less")
    stats: dict[str, float] = Field(default_factory=dict)
    links: list[RevelationLink]
    image_prompt: str = Field(description=IMAGE_PROMPT)
    tags: list[str] = Field(default_factory=list)
    mechanic: NaturalLaw | None = Field(default=None, description="ONLY if the type is natural_law: how the law works in the world. {{ natural_laws }}")
    commodity: CommodityKind | None = Field(default=None, description="ONLY if the type is resource: what it yields when worked")
    material: MaterialKind | None = Field(default=None, description="ONLY if the type is resource yielding ore, stone or timber: the material")
    resource_mechanics: list[ResourceMechanic] = Field(default_factory=list, description="ONLY if the type is resource: its special rules, if any")
    structure_kind: StructureKind | None = Field(default=None, description="ONLY if the type is structure: what kind of work it is")
