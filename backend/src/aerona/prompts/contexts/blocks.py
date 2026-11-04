from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.node import NodeKind
from aerona.prompts.contexts.base import ContextItem, PromptContext, RulesContext
from aerona.prompts.contexts.common import ChronicleRow, EntityLineItem, LabelValue, LexiconWord, NamedRecord, NamingRuleItem, TiredImages, WorldItem
from aerona.prompts.contexts.economy_depth import EconomyBlock


class CreatorMood(ContextItem):
    contentment: int
    anger: int
    attention: int
    loneliness: int


class EpicSummary(ContextItem):
    title: str
    line: str


class WorldNaming(ContextItem):
    id: int
    name: str
    naming: NamingRuleItem


class ClimateLine(ContextItem):
    name: str
    since_age: int
    description: str


class SeasonLine(ContextItem):
    position: int
    name: str
    growth: int
    campaign: int


class AgeStar(ContextItem):
    id: int
    name: str
    domain: str | None = None
    sky_world: str | None = None


class LawLine(ContextItem):
    id: int
    name: str
    description: str


class WorldHeaderContext(RulesContext):
    world_name: str
    age: int
    world_year: int
    god_name: str
    god_title: str | None = None
    short: bool = False
    god_temperament: str | None = None
    god_note: str | None = None
    mood: CreatorMood | None = None
    epic: EpicSummary | None = None
    prohibitions: list[str] = Field(default_factory=list)
    desire: str | None = None
    cosmology: str
    tone: str
    naming_rule: NamingRuleItem
    dialect_world: WorldNaming | None = None
    dialects: list[WorldNaming] = Field(default_factory=list)
    doom: int = 0
    doom_threshold: int
    climate: ClimateLine | None = None
    seasons: list[SeasonLine] = Field(default_factory=list)
    year_days: int | None = None
    age_star: AgeStar | None = None
    laws: list[LawLine] = Field(default_factory=list)


class DialectBlockContext(PromptContext):
    worlds: list[WorldNaming]


class WorldLineContext(PromptContext):
    id: int
    name: str
    type_label: str
    star_name: str | None = None
    star_type: str | None = None
    gravity: str
    atmosphere: str
    time_factor: float
    leak: int = 0
    cosmology: str | None = None


class CosmosWorld(ContextItem):
    id: int
    name: str
    type_label: str
    star_name: str | None = None
    regions: int
    peoples: int
    settlements: int
    gravity: str
    atmosphere: str
    time_factor: float = 1.0
    discovery_label: str | None = None


class CosmosLinesContext(PromptContext):
    worlds: list[CosmosWorld]


class EntityLineContext(PromptContext):
    entity: EntityLineItem
    with_location: bool = True


class BondEndpoint(ContextItem):
    kind: NodeKind
    id: int
    name: str


class BondLine(ContextItem):
    label: str
    other: BondEndpoint
    description: str | None = None


class BondLinesContext(PromptContext):
    outgoing: list[BondLine] = Field(default_factory=list)
    incoming: list[BondLine] = Field(default_factory=list)


class EntityAuthor(StrEnum):
    WORLD = "world"
    CREATOR = "creator"
    SON = "son"
    UNKNOWN = "unknown"


class ClassShare(ContextItem):
    label: str
    share: int
    satisfaction: int


class CommunityRelationLine(ContextItem):
    id: int
    name: str
    label: str
    value: int
    blood_feud: bool = False


class WarLine(ContextItem):
    id: int
    name: str
    clashes: int


class SocietyLines(ContextItem):
    tier_label: str | None = None
    sanity: int | None = None
    clouded: bool = False
    classes: list[ClassShare] = Field(default_factory=list)
    relations: list[CommunityRelationLine] = Field(default_factory=list)
    wars: list[WarLine] = Field(default_factory=list)


class SocietyLinesContext(PromptContext):
    society: SocietyLines


class EntityDetailContext(PromptContext):
    entity: EntityLineItem
    author: EntityAuthor
    author_son: NamedRecord | None = None
    age: int
    world: WorldItem | None = None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    stats: list[LabelValue] = Field(default_factory=list)
    description: str
    history: str | None = None
    fate_note: str | None = None
    outgoing: list[BondLine] = Field(default_factory=list)
    incoming: list[BondLine] = Field(default_factory=list)
    contents: list[EntityLineItem] = Field(default_factory=list)
    lexicon: list[LexiconWord] | None = None
    society: SocietyLines | None = None
    facts: list[str] = Field(default_factory=list)
    body: list[str] = Field(default_factory=list)
    mind: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    chain: str | None = None
    economy: EconomyBlock | None = None


class RecentChronicleContext(PromptContext):
    rows: list[ChronicleRow]


class ThreadLine(ContextItem):
    id: int
    age: int
    worlds: list[str] = Field(default_factory=list)
    advanced: int = 0
    last_age: int | None = None
    text: str
    related_ids: list[int] = Field(default_factory=list)


class ThreadLinesContext(PromptContext):
    threads: list[ThreadLine]
    more: int = 0
    elsewhere: int = 0


class RelationToViewer(ContextItem):
    label: str
    value: int


class SiblingLine(ContextItem):
    id: int
    name: str
    title: str
    rarity_label: str
    stars: int
    existence_label: str
    domain_1: str
    domain_2: str
    world: str | None = None
    other_world: bool = False
    level: int
    hp: int
    max_hp: int
    faith: int
    fame: int
    status_label: str | None = None
    sleep_left: int | None = None
    relation: RelationToViewer | None = None
    covenant: bool = False
    rebel: bool = False


class SiblingsContext(PromptContext):
    siblings: list[SiblingLine]


class PowerLine(ContextItem):
    name: str
    effect_text: str | None = None
    unlock_level: int | None = None
    description: str


class PowersContext(PromptContext):
    powers: list[PowerLine]


class TreeNode(ContextItem):
    depth: int
    entity: EntityLineItem


class LocationTreeContext(PromptContext):
    nodes: list[TreeNode]


class LanguageLine(ContextItem):
    id: int
    name: str
    subtype: str | None = None
    word_count: int
    speakers: list[str] = Field(default_factory=list)
    dead: bool = False
    words: list[LexiconWord] = Field(default_factory=list)


class LanguageLinesContext(PromptContext):
    languages: list[LanguageLine]


class RegionGeography(ContextItem):
    id: int
    name: str
    elevation_label: str
    coastal: bool = False
    size_label: str
    terrain: list[str] = Field(default_factory=list)
    neighbours: list[NamedRecord] = Field(default_factory=list)
    land: str | None = None
    soil: str | None = None
    climate: str | None = None
    river: str | None = None
    scars: list[str] = Field(default_factory=list)
    harvest: str | None = None
    ley: list[NamedRecord] = Field(default_factory=list)
    use: str | None = None
    nexus: str | None = None
    weather: str | None = None


class GeographyLinesContext(PromptContext):
    known_regions: int
    regions: list[RegionGeography]


class SummarySection(StrEnum):
    PANTHEON = "pantheon"
    THREADS = "threads"
    EVENTS = "events"
    COSMOS = "cosmos"
    GEOGRAPHY = "geography"
    LANGUAGES = "languages"
    MAP = "map"
    LEGENDS = "legends"


class ForeignGodLine(ContextItem):
    id: int
    name: str
    title: str | None = None
    domains: str | None = None
    power: int
    attitude: int
    strength: int | None = None
    will: int | None = None
    charisma: int | None = None
    cunning: int | None = None
    powers: list[str] = Field(default_factory=list)


class RouteLine(ContextItem):
    id: int
    world_a: str
    world_b: str
    method_label: str
    duration: int


class WorldSummaryContext(RulesContext):
    for_son: bool
    section: SummarySection | None = None
    header: str = ""
    pantheon: str
    threads: str
    events: str
    multi_world: bool = False
    cosmos_lines: str = ""
    foreign_gods: list[ForeignGodLine] = Field(default_factory=list)
    routes: list[RouteLine] = Field(default_factory=list)
    geography: str
    geography_total: int
    geography_cut: bool = False
    languages: str
    map: str
    legends: list[EntityLineItem] = Field(default_factory=list)


class MemoryWord(ContextItem):
    age: int
    from_father: bool
    sender: str
    intent_label: str | None = None
    text: str


class MemoryCreation(ContextItem):
    entity: EntityLineItem
    other_world: str | None = None
    fate_note: str | None = None


class RepeatBucket(ContextItem):
    label: str
    count: int


class FolkBeliefLine(ContextItem):
    people: str
    name: str
    story: str


class SonMemoryContext(RulesContext):
    full: bool = False
    plan: str | None = None
    plan_age: int | None = None
    plan_years: int | None = None
    plan_stale: bool = False
    closed_since_plan: list[str] = Field(default_factory=list)
    words: list[MemoryWord] = Field(default_factory=list)
    creations: list[MemoryCreation] = Field(default_factory=list)
    creations_total: int = 0
    current_world: WorldItem | None = None
    repeats: list[RepeatBucket] = Field(default_factory=list)
    worshippers: list[NamedRecord] = Field(default_factory=list)
    extra_worshippers: int = 0
    recollections: list[ChronicleRow] = Field(default_factory=list)
    about: list[ChronicleRow] = Field(default_factory=list)
    beliefs: list[FolkBeliefLine] = Field(default_factory=list)


class SkyCalendarContext(PromptContext):
    age: int
    period: int


class BudgetTrailerContext(PromptContext):
    hidden_lines: int
    hint: str


class InspectSiblingContext(PromptContext):
    id: int
    name: str
    title: str
    rarity_label: str
    domain_1: str
    domain_2: str
    level: int
    status_label: str
    appearance: str | None = None
    temperament: str | None = None
    speech: str | None = None
    known_powers: list[str] = Field(default_factory=list)
    strength: int
    wisdom: int
    cunning: int
    charisma: int
    will: int
    hp: int
    max_hp: int
    faith: int
    fame: int
    relation: RelationToViewer
    covenant: bool = False
    creations: list[EntityLineItem] = Field(default_factory=list)


class TiredImagesContext(PromptContext):
    images: TiredImages
