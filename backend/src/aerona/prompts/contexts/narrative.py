from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.entity import EntityType
from aerona.prompts.contexts.base import ContextItem, LoreContext, LoreRulesContext
from aerona.prompts.contexts.blocks import FolkBeliefLine
from aerona.prompts.contexts.common import ChronicleRow, EntityLineItem, LabelValue, NamingRuleItem, SonBrief, TiredImages
from aerona.prompts.contexts.fate import WorldEvents


class NameProblem(StrEnum):
    DIALECT = "dialect"
    SIMILAR = "similar"
    WEAK = "weak"
    TIRED = "tired"


class DialectWarning(ContextItem):
    id: int
    name: str
    root: str
    letters: list[str] = Field(default_factory=list)
    problems: list[NameProblem] = Field(default_factory=lambda: [NameProblem.DIALECT])
    similar_to: str | None = None
    tired_words: list[str] = Field(default_factory=list)


class NamingContext(LoreContext):
    world_name: str
    target_world: str | None = None
    world_header: str
    records: list[str]
    dialect_warnings: list[DialectWarning] = Field(default_factory=list)
    tired_images: TiredImages = Field(default_factory=TiredImages)


class HistorianEntry(ContextItem):
    people: EntityLineItem
    world: str | None = None
    society: str = ""
    previous_historian: str | None = None
    previous_age: int | None = None
    previous_opening: str | None = None


class BeliefPair(ContextItem):
    people_id: int
    people_name: str
    son_id: int
    son_name: str
    son_title: str
    domain_1: str
    domain_2: str
    known_name: str | None = None
    worshipped: bool = False


class VoicesContext(LoreRulesContext):
    world_name: str
    world_header: str
    age: int
    age_events: str = ""
    world_events: list[WorldEvents] = Field(default_factory=list)
    historians: list[HistorianEntry] = Field(default_factory=list)
    beliefs: list[BeliefPair] = Field(default_factory=list)


class DeepenEntityContext(LoreRulesContext):
    world_name: str
    world_header: str
    entity_type: EntityType
    entity_detail: str
    creator_son: SonBrief | None = None
    bond_lines: list[str] = Field(default_factory=list)
    recent_events: str = ""
    tired_images: TiredImages = Field(default_factory=TiredImages)


class CelestialKind(StrEnum):
    WORLD = "world"
    STAR = "star"


class DeepenCelestialContext(LoreRulesContext):
    world_name: str
    world_header: str
    kind: CelestialKind
    name: str
    detail_lines: list[str] = Field(default_factory=list)
    lore: str = ""
    neighbour_lines: list[str] = Field(default_factory=list)
    recent_events: str = ""
    tired_images: TiredImages = Field(default_factory=TiredImages)


class GodKnown(ContextItem):
    title: str | None = None
    appearance: str | None = None
    temperament: str | None = None
    note: str | None = None


class EpicSon(ContextItem):
    name: str
    title: str
    rarity_label: str
    domain_1: str
    domain_2: str
    status_label: str | None = None
    rebel: bool = False
    loyalty: int


class EpicWorld(ContextItem):
    name: str
    type_label: str
    age: int


class AgeSummary(ContextItem):
    age: int
    name: str
    summary: str


class TraceRow(ContextItem):
    age: int
    year: int
    text: str


class CreatorEpicContext(LoreRulesContext):
    world_name: str
    world_header: str
    god_name: str
    known: GodKnown
    cosmology: str
    sons: list[EpicSon] = Field(default_factory=list)
    worlds: list[EpicWorld] = Field(default_factory=list)
    ages: list[AgeSummary] = Field(default_factory=list)
    traces: list[TraceRow] = Field(default_factory=list)
    beliefs: list[FolkBeliefLine] = Field(default_factory=list)
    listed_ages: int = 0


class CreatorDeepenContext(LoreRulesContext):
    world_name: str
    world_header: str
    god_name: str
    known: GodKnown
    cosmology: str
    epic_line: str | None = None
    sons: list[SonBrief] = Field(default_factory=list)
    traces: list[TraceRow] = Field(default_factory=list)


class HomeWorld(ContextItem):
    name: str
    type_label: str
    dialect: NamingRuleItem | None = None
    cosmology: str | None = None


class ForeignPowerLine(ContextItem):
    name: str
    effect_label: str


class ForeignGodKnown(ContextItem):
    title: str | None = None
    domains: str | None = None
    description: str | None = None
    dead: bool = False
    death_age: int | None = None
    status_label: str
    power: int
    attitude: int
    contact: bool = False
    stats: list[LabelValue] = Field(default_factory=list)
    powers: list[ForeignPowerLine] = Field(default_factory=list)
    personality: list[LabelValue] = Field(default_factory=list)


class WorshipperLine(ContextItem):
    name: str
    type_label: str
    subtype: str | None = None


class ForeignGodDeepenContext(LoreRulesContext):
    world_name: str
    world_header: str
    name: str
    home_world: HomeWorld | None = None
    known: ForeignGodKnown
    worshippers: list[WorshipperLine] = Field(default_factory=list)
    chronicle: list[ChronicleRow] = Field(default_factory=list)


class EpicCreation(ContextItem):
    name: str
    type_label: str
    subtype: str | None = None
    age: int
    status_label: str | None = None


class SonEpicContext(LoreContext):
    world_name: str
    world_header: str
    name: str
    title: str
    rarity_label: str
    stars: int
    domain_1: str
    domain_2: str
    temperament: str
    traits: list[str] = Field(default_factory=list)
    obsession: str
    secret: str
    plan: str | None = None
    creations: list[EpicCreation] = Field(default_factory=list)
    records: list[ChronicleRow] = Field(default_factory=list)
    listed_ages: int = 0
