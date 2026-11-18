from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreContext, LoreRulesContext
from aerona.prompts.contexts.common import EntityLineItem, WorldItem
from aerona.prompts.contexts.fate import WorldEvents


class ChroniclerSystemContext(LoreContext):
    world_name: str


class ChroniclerLink(ContextItem):
    age: int
    name: str
    who: str


class ChroniclerContinuity(ContextItem):
    current: ChroniclerLink | None = None
    chain: list[ChroniclerLink] = Field(default_factory=list)


class NameKind(ContextItem):
    name: str
    type_label: str
    mortal: bool = False
    subtype: str | None = None


class FactRecord(ContextItem):
    id: int
    name: str


class FactActor(ContextItem):
    ref: str
    id: int
    name: str
    world: str | None = None
    deeds: list[str] = Field(default_factory=list)
    deed_count: int = 0
    records: list[FactRecord] = Field(default_factory=list)


class ContestKind(StrEnum):
    WAR = "war"
    DUEL = "duel"
    GOD_CONFLICT = "god_conflict"


class FactOutcome(ContextItem):
    ref: str
    kind: ContestKind
    contest: str | None = None
    winner_id: int
    winner: str
    loser_id: int
    loser: str
    score: str | None = None


class FactDraw(ContextItem):
    son: str
    text: str


class FactHistory(ContextItem):
    name: str
    kind: str
    since: int
    ended: int | None = None
    within: str | None = None


class FactEvent(ContextItem):
    ref: str
    category: str
    world: str | None = None
    text: str
    repeats: int = 1
    name: str | None = None
    place: str | None = None
    account: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    more_steps: int = 0
    cause: str | None = None


class FactTale(ContextItem):
    subject: str
    template: str
    stage: str
    outcome: str


class FactPayoff(ContextItem):
    kind: str
    since: int
    subject: str | None = None
    text: str


class FactVerdict(ContextItem):
    ref: str
    text: str
    required: bool = True


class ChroniclerFactSheet(ContextItem):
    creator: FactActor
    sons: list[FactActor] = Field(default_factory=list)
    outcomes: list[FactOutcome] = Field(default_factory=list)
    draws: list[FactDraw] = Field(default_factory=list)
    events: list[FactEvent] = Field(default_factory=list)
    histories: list[FactHistory] = Field(default_factory=list)
    tales: list[FactTale] = Field(default_factory=list)
    payoffs: list[FactPayoff] = Field(default_factory=list)
    verdicts: list[FactVerdict] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)


class ChroniclerUserContext(LoreRulesContext):
    world_header: str
    age: int
    worlds: list[WorldItem] = Field(default_factory=list)
    missing_worlds: list[WorldItem] = Field(default_factory=list)
    previous_names: list[str] = Field(default_factory=list)
    continuity: ChroniclerContinuity = Field(default_factory=ChroniclerContinuity)
    name_kinds: list[NameKind] = Field(default_factory=list)
    previous_verdicts: list[str] = Field(default_factory=list)
    events: list[WorldEvents] = Field(default_factory=list)
    engine_notes: list[str] = Field(default_factory=list)
    chains: list[str] = Field(default_factory=list)
    event_phases: list[str] = Field(default_factory=list)
    pending: list[EntityLineItem] = Field(default_factory=list)
    facts: ChroniclerFactSheet | None = None
    prehistories: list[str] = Field(default_factory=list)


class AuditFindingItem(ContextItem):
    kind: str
    ref: str | None = None
    name: str | None = None
    world: str | None = None
    sentence: str | None = None
    detail: str | None = None
    stated: str | None = None
    actual: str | None = None


class ChroniclerAuditFixContext(LoreRulesContext):
    facts: ChroniclerFactSheet
    findings: list[AuditFindingItem] = Field(default_factory=list)
    narrative: str
    worlds: list[WorldItem] = Field(default_factory=list)
    sections: dict[int, str] = Field(default_factory=dict)
