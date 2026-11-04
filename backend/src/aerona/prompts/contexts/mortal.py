from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, PromptContext, RulesContext
from aerona.prompts.contexts.blocks import RouteLine
from aerona.prompts.contexts.common import ChronicleRow, EntityLineItem, LabelValue, LexiconWord, NamedRecord, TiredImages


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
    tics: list[str] = Field(default_factory=list)
    tired_images: TiredImages = Field(default_factory=TiredImages)


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


class StoresLine(ContextItem):
    community: str
    materials: list[str] = Field(default_factory=list)
    short: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    prices: list[str] = Field(default_factory=list)
    currency: str = ""
    debts: list[str] = Field(default_factory=list)
    loans: list[str] = Field(default_factory=list)
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
    herds: list[str] = Field(default_factory=list)
    beasts: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    wealth: str = ""
    loyalty: str = ""
    labour: list[str] = Field(default_factory=list)


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
    home: HomeLine | None = None
    mentions: list[ChronicleRow] = Field(default_factory=list)
    languages: str = ""
    other_worlds: str = ""
    routes: list[RouteLine] = Field(default_factory=list)
    expeditions: list[ExpeditionLine] = Field(default_factory=list)
