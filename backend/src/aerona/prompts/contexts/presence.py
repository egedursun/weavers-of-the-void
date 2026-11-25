from pydantic import Field

from aerona.domain.enums.presence import PresenceGuise
from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, RulesContext


class PresenceBlock(ContextItem):
    title: str
    text: str


class PresenceAct(ContextItem):
    tool: str
    outcome: str
    failed: bool = False


class PresenceRemembered(ContextItem):
    ordinal: int
    player_text: str
    reply_text: str
    acts: list[PresenceAct] = Field(default_factory=list)


class PresenceTraceLine(ContextItem):
    kind: str
    text: str
    tool: str = ""


class PresenceSystemContext(LoreRulesContext):
    speaker_name: str
    epithet: str = ""
    kind_label: str
    world_name: str
    caller: str
    guise: PresenceGuise
    on_record: bool
    may_act: bool = False
    acting_paused: bool = False
    action_points: int = 0
    read_tools: list[str] = Field(default_factory=list)
    dead: bool = False
    death_epoch: int | None = None
    death_how: str = ""
    death_line: str = ""
    self_lines: list[str] = Field(default_factory=list)
    blocks: list[PresenceBlock] = Field(default_factory=list)


class PresenceUserContext(LoreRulesContext):
    caller: str
    player_text: str
    player_language: str = ""
    forgotten: int = 0
    remembered: list[PresenceRemembered] = Field(default_factory=list)
    trace: list[PresenceTraceLine] = Field(default_factory=list)


class PresenceClosingContext(RulesContext):
    caller: str
    guise: PresenceGuise
    player_text: str
    reply_text: str
    player_language: str = ""
    acts: list[PresenceAct] = Field(default_factory=list)
