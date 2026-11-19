from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, PromptContext, RulesContext
from aerona.prompts.contexts.blocks import RouteLine
from aerona.prompts.contexts.common import ChronicleRow, EntityLineItem, LabelValue, LexiconWord, NamedRecord


class MortalTurnSystemContext(LoreRulesContext):
    name: str
    world_name: str
    type_label: str
    subtype: str | None = None
    action_points: int
    sanity: int | None = None
    clouded: bool = False
    paid_tools: list[str] = Field(default_factory=list)
    free_tools: list[str] = Field(default_factory=list)
    captor: str | None = None


class FallenSonTurnContext(LoreRulesContext):
    son_name: str
    title: str
    body_name: str
    world_name: str
    memory: str
    body: list[str] = Field(default_factory=list)
    remnant: list[str] = Field(default_factory=list)
    existence: int
    restoration_existence: int
    knows_true_name: bool = False
    action_points: int
    paid_tools: list[str] = Field(default_factory=list)
    free_tools: list[str] = Field(default_factory=list)


class MortalTurnUserContext(PromptContext):
    age: int
    creator_name: str
    manifestations: list[str] = Field(default_factory=list)
    dreams: list[str] = Field(default_factory=list)
    context: str
    opportunities: str = ""
    resumed: bool = False
    continuation: str = ""
    actions_left: int


class MortalGodKind(StrEnum):
    SON = "son"
    FOREIGN_GOD = "foreign_god"
    NONE = "none"


class MortalGod(ContextItem):
    kind: MortalGodKind
    id: int = 0
    name: str = ""
    title: str | None = None
    domain_1: str | None = None
    domain_2: str | None = None


class FolkGodName(ContextItem):
    name: str
    son_id: int
    story: str


class MortalLanguage(ContextItem):
    id: int
    name: str
    words: list[LexiconWord] = Field(default_factory=list)


class MortalLand(ContextItem):
    id: int
    name: str
    elevation_label: str | None = None
    coastal: bool = False
    neighbours: list[NamedRecord] = Field(default_factory=list)
    ground: str | None = None
    weather: str | None = None


class HeardRumour(ContextItem):
    age: int
    fidelity: int
    text: str


class KnowledgeItem(ContextItem):
    id: int
    name: str
    branch_label: str
    level: int | None = None


class OwnedResource(ContextItem):
    id: int
    name: str
    abundance: int
    yields: str = ""


class ResearchLine(ContextItem):
    community: str
    current: str = ""
    chooser: str = ""
    choices: list[str] = Field(default_factory=list)
    institutions: list[str] = Field(default_factory=list)
    boosts: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    great_people: list[str] = Field(default_factory=list)
    age: str = ""
    incidents: list[str] = Field(default_factory=list)
    designs: list[str] = Field(default_factory=list)
    theories: list[str] = Field(default_factory=list)
    art_forms: list[str] = Field(default_factory=list)
    epithet: str = ""


class StoresLine(ContextItem):
    community: str
    materials: list[str] = Field(default_factory=list)
    short: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    prices: list[str] = Field(default_factory=list)
    currency: str = ""
    debts: list[str] = Field(default_factory=list)
    loans: list[str] = Field(default_factory=list)
    works: list[str] = Field(default_factory=list)
    job: str = ""


class HomeLine(ContextItem):
    community: str
    tier: str = ""
    order: int | None = None
    crime: int | None = None
    unrest: int | None = None
    social_class: str = ""
    satisfaction: int | None = None
    customs: list[str] = Field(default_factory=list)
    sickness: list[str] = Field(default_factory=list)
    realm: str = ""
    office: str = ""
    house: str = ""
    oaths: list[str] = Field(default_factory=list)
    treaties: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    succession: str = ""
    laws: list[str] = Field(default_factory=list)
    factions: list[str] = Field(default_factory=list)
    wars: list[str] = Field(default_factory=list)
    command: str = ""
    occupied_by: str = ""
    captives: int = 0
    tenets: list[str] = Field(default_factory=list)
    judgement: str = ""
    zeal: int | None = None
    tongues: list[str] = Field(default_factory=list)
    techniques: list[str] = Field(default_factory=list)
    creed: str = ""
    legends: list[str] = Field(default_factory=list)
    traditions: list[str] = Field(default_factory=list)
    prophecies: list[str] = Field(default_factory=list)
    rites: list[str] = Field(default_factory=list)
    treasures: list[str] = Field(default_factory=list)
    wildlife: list[str] = Field(default_factory=list)
    crops: list[str] = Field(default_factory=list)
    pets: list[str] = Field(default_factory=list)
    herds: list[str] = Field(default_factory=list)
    beasts: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    wealth: str = ""
    loyalty: str = ""
    labour: list[str] = Field(default_factory=list)
    works: list[str] = Field(default_factory=list)
    looks: str = ""
    gift: str = ""
    household: str = ""
    dwelling: str = ""
    secrets: list[str] = Field(default_factory=list)
    leverage: list[str] = Field(default_factory=list)
    mask: str = ""
    scheme: str = ""
    true_names: list[str] = Field(default_factory=list)
    beliefs: list[str] = Field(default_factory=list)
    letters: list[str] = Field(default_factory=list)
    opinions: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    estates: list[str] = Field(default_factory=list)
    gatherings: list[str] = Field(default_factory=list)
    sites: list[str] = Field(default_factory=list)
    proposals: list[str] = Field(default_factory=list)
    cases: list[str] = Field(default_factory=list)
    abroad: list[str] = Field(default_factory=list)
    affairs: list[str] = Field(default_factory=list)
    dominion: list[str] = Field(default_factory=list)
    magic: list[str] = Field(default_factory=list)
    speech: list[str] = Field(default_factory=list)
    contagion: list[str] = Field(default_factory=list)
    streets: list[str] = Field(default_factory=list)
    courts: list[str] = Field(default_factory=list)
    crowds: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    rule: list[str] = Field(default_factory=list)
    land: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    sacred: list[str] = Field(default_factory=list)
    pursuits: list[str] = Field(default_factory=list)
    tales: list[str] = Field(default_factory=list)
    folkways: list[str] = Field(default_factory=list)
    folk_customs: list[str] = Field(default_factory=list)
    daily_life: list[str] = Field(default_factory=list)
    kin: list[str] = Field(default_factory=list)
    childhood: list[str] = Field(default_factory=list)
    unions_and_birth: list[str] = Field(default_factory=list)
    youth: list[str] = Field(default_factory=list)
    population_policy: list[str] = Field(default_factory=list)
    commerce: list[str] = Field(default_factory=list)
    public_works: list[str] = Field(default_factory=list)
    media: list[str] = Field(default_factory=list)
    oratory: list[str] = Field(default_factory=list)
    folk_knowledge: list[str] = Field(default_factory=list)
    endowments: list[str] = Field(default_factory=list)
    the_dead: list[str] = Field(default_factory=list)
    practices: list[str] = Field(default_factory=list)
    sky: list[str] = Field(default_factory=list)
    water: list[str] = Field(default_factory=list)
    body_systems: list[str] = Field(default_factory=list)
    plants: list[str] = Field(default_factory=list)
    forecasting: list[str] = Field(default_factory=list)
    standing: list[str] = Field(default_factory=list)
    crafts: list[str] = Field(default_factory=list)
    climes: list[str] = Field(default_factory=list)
    belonging: list[str] = Field(default_factory=list)
    eras: list[str] = Field(default_factory=list)
    nature: list[str] = Field(default_factory=list)
    means: list[str] = Field(default_factory=list)
    economy: list[str] = Field(default_factory=list)
    honours: list[str] = Field(default_factory=list)
    record_keeping: list[str] = Field(default_factory=list)
    world_nature: list[str] = Field(default_factory=list)
    biology: list[str] = Field(default_factory=list)
    grounds: list[str] = Field(default_factory=list)
    made_world: list[str] = Field(default_factory=list)
    powers: list[str] = Field(default_factory=list)
    living: list[str] = Field(default_factory=list)
    fortune: list[str] = Field(default_factory=list)
    ways_of_life: list[str] = Field(default_factory=list)
    home_and_trust: list[str] = Field(default_factory=list)


class ExpeditionLine(ContextItem):
    intent_label: str
    remaining: int
    people: int


class MortalContextContext(RulesContext):
    full: bool = False
    world_header: str
    world_line: str
    self_detail: str
    character: list[LabelValue] = Field(default_factory=list)
    god: MortalGod = Field(default_factory=lambda: MortalGod(kind=MortalGodKind.NONE))
    folk_gods: list[FolkGodName] = Field(default_factory=list)
    language: MortalLanguage | None = None
    land: MortalLand | None = None
    near: list[EntityLineItem] = Field(default_factory=list)
    recent_events: list[ChronicleRow] = Field(default_factory=list)
    known: list[KnowledgeItem] = Field(default_factory=list)
    world_knowledge: list[KnowledgeItem] = Field(default_factory=list)
    resources: list[OwnedResource] = Field(default_factory=list)
    items: list[NamedRecord] = Field(default_factory=list)
    stores: StoresLine | None = None
    research: ResearchLine | None = None
    home: HomeLine | None = None
    mentions: list[ChronicleRow] = Field(default_factory=list)
    rumours: list[HeardRumour] = Field(default_factory=list)
    records: str = ""
    languages: str = ""
    other_worlds: str = ""
    routes: list[RouteLine] = Field(default_factory=list)
    expeditions: list[ExpeditionLine] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    registers: list[str] = Field(default_factory=list)
