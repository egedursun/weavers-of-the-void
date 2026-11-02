from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.agent import ToolBlock, TurnCounter
from aerona.domain.enums.rarity import Rarity
from aerona.prompts.contexts.opportunities import CreatorHintKind


class OpportunityLineView(ApiModel):
    kind: str
    text: str
    tension: bool
    tools: list[str]


class OpportunityLines(ApiModel):
    subject_id: int
    lines: list[OpportunityLineView]


class CreatorHintLine(ApiModel):
    kind: CreatorHintKind
    text: str


class CreatorHintLines(ApiModel):
    lines: list[CreatorHintLine]


class ToolPreviewView(ApiModel):
    name: str
    description: str
    fields: dict[str, str]
    action_cost: int
    essence_cost: int
    read_only: bool
    long_job: bool
    minimum_rarity: Rarity | None


class BlockedToolView(ApiModel):
    name: str
    reason: ToolBlock
    minimum_rarity: Rarity | None


class TurnCounterView(ApiModel):
    counter: TurnCounter
    value: int


class SonToolsView(ApiModel):
    son_id: int
    rarity: Rarity
    epoch: int
    action_points_left: int | None
    available: list[ToolPreviewView]
    blocked: list[BlockedToolView]
    counters: list[TurnCounterView]


class MortalAgentContext(ApiModel):
    entity_id: int
    name: str
    epoch: int
    action_points: int
    system_prompt: str
    user_prompt: str
    available: list[ToolPreviewView]
    blocked: list[BlockedToolView]
    counters: list[TurnCounterView]


class DreamView(ApiModel):
    id: int
    epoch: int
    sender: NodeRef | None
    recipient: NodeRef | None
    text: str
    is_read: bool


class DreamInbox(ApiModel):
    entity_id: int
    received: list[DreamView]
    sent: list[DreamView]
