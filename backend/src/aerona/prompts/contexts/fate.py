from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreContext, LoreRulesContext, PromptContext, RulesContext
from aerona.prompts.contexts.common import NamedRecord


class FateSystemContext(LoreContext):
    world_name: str


class PrescreenKind(StrEnum):
    UNBOUND = "unbound"
    SHORT_DESCRIPTION = "short_description"
    CONFUSABLE_NAME = "confusable_name"
    OFF_DOMAIN_POWER = "off_domain_power"
    LOCATION_IN_OTHER_WORLD = "location_in_other_world"


class PrescreenWarning(ContextItem):
    kind: PrescreenKind
    matches: list[str] = Field(default_factory=list)
    other_name: str | None = None
    power_level: int | None = None
    domain: str | None = None


class PrescreenWarningsContext(PromptContext):
    warnings: list[PrescreenWarning]


class FateCreationEntryContext(PromptContext):
    detail: str
    warnings: list[PrescreenWarning] = Field(default_factory=list)


class WorldRecordLine(ContextItem):
    id: int
    name: str
    kind_label: str


class FateThreadLine(ContextItem):
    id: int
    age: int
    advancers: list[str] = Field(default_factory=list)
    advance_count: int = 0
    stagnant_ages: int = 0
    text: str


class FateJudgmentContext(LoreRulesContext):
    age: int
    min_close: int
    new_max: int
    close_candidates: list[int] = Field(default_factory=list)
    world_summary: str
    age_events: str = ""
    engine_notes: list[str] = Field(default_factory=list)
    chains: list[str] = Field(default_factory=list)
    new_creations: list[str] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
    world_records: list[WorldRecordLine] = Field(default_factory=list)
    prophecies: list[str] = Field(default_factory=list)
    threads: list[FateThreadLine] = Field(default_factory=list)
    pantheon: list[NamedRecord] = Field(default_factory=list)
    languages: list[NamedRecord] = Field(default_factory=list)


class FateExtraJudgmentContext(PromptContext):
    world_header: str
    entries: list[str]


class AgeEventRow(ContextItem):
    text: str
    repeats: int = 1


class AgeEventsContext(PromptContext):
    rows: list[AgeEventRow]
    limit: int
    trim_min: int


class WorldEvents(ContextItem):
    world_id: int | None = None
    world_name: str | None = None
    rows: list[AgeEventRow] = Field(default_factory=list)


class AgeEventsByWorldContext(RulesContext):
    sections: list[WorldEvents]
    limit: int
