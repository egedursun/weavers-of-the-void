from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, computed_field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.domain.enums.divine_will import (
    AttachmentKind,
    AttachmentStatus,
    ConfirmationReason,
    ConfirmationStatus,
    CycleEventKind,
    CycleNotice,
    CycleStatus,
    DivineWillMode,
)
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import Toolset

PLAYER_TEXT_MAX = 100000


class ConfirmationDecision(StrEnum):
    APPROVE = "approve"
    DECLINE = "decline"


class WillCycleRequest(RequestModel):
    text: str = Field(min_length=1, max_length=PLAYER_TEXT_MAX)
    mode: DivineWillMode = DivineWillMode.COMMAND
    attachment_ids: list[int] = Field(default_factory=list)


class WillDecisionRequest(RequestModel):
    decision: ConfirmationDecision


class WillEventView(ApiModel):
    id: int
    ordinal: int
    kind: CycleEventKind
    tool: str
    payload: dict[str, Any]
    handle: str
    created_at: datetime

    @computed_field
    def notice(self) -> CycleNotice | None:
        value = self.payload.get("notice")
        return CycleNotice(value) if value in NOTICES else None


NOTICES = frozenset(item.value for item in CycleNotice)


class WillConfirmationView(ApiModel):
    id: int
    cycle_id: int
    action_id: str
    input: dict[str, Any]
    reason: ConfirmationReason
    preview: dict[str, Any]
    status: ConfirmationStatus
    decided_at: datetime | None
    ledger_entry_id: int | None
    created_at: datetime


class WillCycleAttachment(ApiModel):
    id: int
    kind: AttachmentKind
    filename: str
    mime: str
    size: int
    status: AttachmentStatus
    seen_by_model: bool
    note: str


class WillCycleView(ApiModel):
    id: int
    session_id: int
    ordinal: int
    mode: DivineWillMode
    epoch: int
    status: CycleStatus
    player_text: str
    final_text: str
    model: str
    input_tokens: int
    output_tokens: int
    steps: int
    error: str
    started_at: datetime
    finished_at: datetime | None
    events: list[WillEventView]
    confirmations: list[WillConfirmationView]
    attachments: list[WillCycleAttachment]


class WillCapabilitiesView(ApiModel):
    enabled: bool
    images: bool
    probed: bool
    note: str
    model: str
    upload_max_files: int
    upload_max_mb: int


class WillSessionSummary(ApiModel):
    id: int
    title: str
    opened_epoch: int
    opened_at: datetime
    closed_epoch: int | None
    closed_at: datetime | None
    cycle_count: int


class WillSessionView(ApiModel):
    session: WillSessionSummary
    cycles: list[WillCycleView]
    memory_boundary: int
    has_earlier: bool


class WillActiveView(ApiModel):
    session: WillSessionSummary | None
    cycles: list[WillCycleView]
    memory_boundary: int
    has_earlier: bool
    remembered_cycles: int
    running_cycle_id: int | None
    capabilities: WillCapabilitiesView


class WillSessionList(ApiModel):
    sessions: list[WillSessionSummary]


class WillCycleAccepted(ApiModel):
    cycle_id: int
    session_id: int
    ordinal: int


class WillModeView(ApiModel):
    mode: DivineWillMode
    name: str
    purpose: str
    changes_world: bool
    toolsets: list[Toolset]
    tools: list[DivineWillToolId]


class WillModesView(ApiModel):
    modes: list[WillModeView]
