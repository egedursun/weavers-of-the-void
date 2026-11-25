from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, RulesContext


class WillModeLine(ContextItem):
    value: str
    name: str
    purpose: str
    current: bool = False


class WillToolStep(ContextItem):
    tool: str
    arguments: str
    outcome: str
    handle: str = ""
    failed: bool = False


class RememberedExchange(ContextItem):
    ordinal: int
    mode_name: str
    player_text: str
    final_text: str
    steps: list[WillToolStep] = Field(default_factory=list)


class WillTraceLine(ContextItem):
    kind: str
    text: str
    tool: str = ""
    handle: str = ""


class WillAttachmentLine(ContextItem):
    attachment_id: int
    filename: str
    kind_name: str
    seen: bool = True
    note: str = ""


class DivineWillSystemContext(LoreRulesContext):
    world_name: str
    creator_name: str
    mode_name: str
    modes: list[WillModeLine] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class DivineWillTranslateContext(RulesContext):
    language: str
    text: str


class DivineWillUserContext(LoreRulesContext):
    mode_name: str
    player_text: str
    player_language: str = ""
    forgotten: int = 0
    remembered: list[RememberedExchange] = Field(default_factory=list)
    attachments: list[WillAttachmentLine] = Field(default_factory=list)
    trace: list[WillTraceLine] = Field(default_factory=list)
