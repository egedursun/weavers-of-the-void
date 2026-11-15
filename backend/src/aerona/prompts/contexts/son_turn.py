from enum import StrEnum

from pydantic import Field

from aerona.domain.enums.son import ReputationLabel
from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, PromptContext, RulesContext


class StatValue(ContextItem):
    label: str
    value: int


class Passions(ContextItem):
    loyalty: int
    ambition: int
    wrath: int
    mercy: int


class ExistenceProfile(ContextItem):
    nature: str | None = None
    state_label: str | None = None
    manifestation: str | None = None
    true_name: str | None = None
    known_by: int = 0
    names_known: list[str] = Field(default_factory=list)


class AnchorLine(ContextItem):
    id: int
    name: str
    status_label: str


class SonTurnSystemContext(LoreRulesContext):
    son_name: str
    son_title: str
    god_name: str
    world_name: str
    rarity_label: str
    stars: int
    level: int
    domain_1: str
    domain_2: str
    existence: ExistenceProfile
    appearance: str
    temperament: str
    obsession: str
    fear: str
    speech_style: str
    secret: str
    stats: list[StatValue]
    passions: Passions
    hp: int
    max_hp: int
    wounds: list[str] = Field(default_factory=list)
    mind: list[str] = Field(default_factory=list)
    essence: int
    max_essence: int
    faith: int
    fame: int
    existence_value: int
    existence_band_label: str
    existence_band_effect: str
    anchor: AnchorLine | None = None
    anchor_held: bool = False
    shrines: list[AnchorLine] = Field(default_factory=list)
    incitements: list[str] = Field(default_factory=list)
    powers: str
    action_points: int
    paid_tools: list[str] = Field(default_factory=list)
    free_tools: list[str] = Field(default_factory=list)
    power_ceiling: int
    sky_calendar: str
    tools: list[str]
    reputation_line: str = ""
    rebel: bool = False
    rebel_prone: bool = False
    creator_wishes: str = ""
    sanity: int | None = None
    clouded: bool = False
    divine: list[str] = Field(default_factory=list)


class SonTurnUserContext(RulesContext):
    age: int
    order: str | None = None
    absolute_order: bool = False
    world_summary: str
    memory: str
    opportunities: str = ""
    faith: str = ""
    changes: list[str] = Field(default_factory=list)
    action_points: int
    resumed: bool = False
    continuation: str = ""


class TurnInterruption(StrEnum):
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    STEP_LIMIT = "step_limit"
    NO_FINAL_WORD = "no_final_word"


class DoneAction(ContextItem):
    tool: str
    summary: str


class LongJobNote(ContextItem):
    tool: str
    summary: str


class TurnContinuationContext(PromptContext):
    reason: TurnInterruption
    error_detail: str | None = None
    done: list[DoneAction] = Field(default_factory=list)
    long_jobs: list[LongJobNote] = Field(default_factory=list)


class ReputationLineContext(PromptContext):
    stance: ReputationLabel
    love: int
    fear: int
    oblivion: int
    unanswered_prayers: int = 0
    passions: list[str] = Field(default_factory=list)


class PassionHint(ContextItem):
    label: str
    hint: str


class ScenarioLine(ContextItem):
    name: str
    description: str
    deadline_epoch: int | None = None


class CreatorWishesContext(PromptContext):
    passions: list[PassionHint] = Field(default_factory=list)
    scenarios: list[ScenarioLine] = Field(default_factory=list)
