from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, RulesContext
from aerona.prompts.contexts.common import LexiconWord, NamingRuleItem


class CouncilMember(ContextItem):
    id: int
    name: str
    title: str
    rarity_label: str
    domain_1: str
    domain_2: str
    rebel: bool = False
    temperament: str
    speech_style: str
    obsession: str
    loyalty: int
    ambition: int
    wrath: int
    plan: str | None = None
    current_world: str | None = None


class CouncilPersonaContext(RulesContext):
    member: CouncilMember


class AgendaKind(StrEnum):
    DOOMSDAY = "doomsday"
    REBEL = "rebel"
    DEAD_SIBLING = "dead_sibling"
    WAR = "war"
    OPEN_THREAD = "open_thread"
    DEFAULT = "default"


class CouncilAgendaContext(RulesContext):
    kind: AgendaKind
    doom: int = 0
    doom_threshold: int = 0
    subject: str = ""


class CouncilRelation(ContextItem):
    a: str
    b: str
    label: str
    value: int
    covenant: bool = False


class CouncilTarget(ContextItem):
    id: int
    name: str
    place: str | None = None


class CouncilSessionContext(LoreRulesContext):
    world_name: str
    creator_name: str
    world_header: str
    topic: str
    god_asked: bool = False
    members: list[CouncilMember]
    absent: list[str] = Field(default_factory=list)
    multi_world: bool = False
    relationships: list[CouncilRelation] = Field(default_factory=list)
    foreign_gods: list[CouncilTarget] = Field(default_factory=list)
    worlds: list[CouncilTarget] = Field(default_factory=list)
    rulings: list[str] = Field(default_factory=list)
    procedure: str = ""
    seated_gods: list[str] = Field(default_factory=list)


class TranslateContext(LoreRulesContext):
    world_name: str
    language_name: str
    language_subtype: str | None = None
    language_description: str
    naming_rule: NamingRuleItem
    syllables: list[str] = Field(default_factory=list)
    lexicon: list[LexiconWord] = Field(default_factory=list)
    text: str
