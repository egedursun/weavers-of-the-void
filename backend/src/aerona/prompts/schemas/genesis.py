from pydantic import Field

from aerona.constants.genesis import FIRST_SONS_CEILING
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
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


class GenesisRegionOutput(OutputModel):
    name: str
    subtype: str = Field(description="continent, sea, ocean, desert belt, archipelago, mountain range…")
    description: str = Field(description="3 to 5 sentences; refer to its neighbours")
    danger: int = Field(ge=0, le=PERCENT_MAX)
    fertility: int = Field(ge=0, le=PERCENT_MAX)
    magic: int = Field(ge=0, le=PERCENT_MAX)
    water: bool = Field(default=False, description="True for a sea or ocean region that is water rather than land")
    image_prompt: str = Field(description="English landscape image prompt. {{ image_prompt_rules }}")


class GenesisCosmicResourceOutput(OutputModel):
    name: str
    description: str
    rule: str = Field(description="How it is extracted, how it is used, what it makes possible")
    side_effect: str = Field(description="The price of long use: mutation, memory loss, the colour of the eyes…")
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
    regions: list[GenesisRegionOutput] = Field(
        description="The first regions the god founded by their own hand: at least one sea or ocean and the rest land regions, neighbouring one another"
    )
    first_celestial: FirstCelestialOutput = Field(description="The first celestial body the god hung in the sky")
    cosmic_resource: GenesisCosmicResourceOutput = Field(
        description="The single substance, unique to the cosmos, that makes travel between worlds (space folding) possible; long use carries a price of the world's own logic (an addiction, a change in the body or mind, a debt, a decay or another cost). It has one deposit in the region at region_index."
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
