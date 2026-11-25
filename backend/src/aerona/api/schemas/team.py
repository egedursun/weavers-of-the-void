from datetime import datetime
from typing import Any

from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.constants.team import PRESENCE_SCREEN_MAX_LENGTH, TEAM_NOTE_MAX_LENGTH
from aerona.domain.enums.accounts import Permission, UniverseRole
from aerona.domain.enums.team import CanonTouch, ProposalStatus, QueuedActSource, QueuedActStatus


class AuthorView(ApiModel):
    account_id: int | None
    name: str


class ConflictChangeView(ApiModel):
    table: str
    node_id: int | None
    field: str | None
    before: float | int | str | None
    after: float | int | str | None
    by: str | None
    by_account_id: int | None
    at: datetime | None


class QueuedActView(ApiModel):
    id: int
    source: QueuedActSource
    action_id: str
    title: str
    payload: dict[str, Any]
    reason: str | None
    author: AuthorView | None
    queued_epoch: int
    queued_at: datetime
    status: QueuedActStatus
    result: str
    applied_at: datetime | None
    ledger_entry_id: int | None
    cancelled_by: AuthorView | None
    plan_id: int | None
    plan_ordinal: int | None
    presence_session_id: int | None
    conflict: list[ConflictChangeView]
    proposal_id: int | None


class CanonProposalView(ApiModel):
    id: int
    action_id: str
    title: str
    payload: dict[str, Any]
    reason: str | None
    preview: dict[str, Any]
    touches: list[CanonTouch]
    held_node_ids: list[int]
    author: AuthorView | None
    proposed_epoch: int
    proposed_at: datetime
    status: ProposalStatus
    decided_by: AuthorView | None
    decided_at: datetime | None
    note: str
    result: str
    ledger_entry_id: int | None


class PresentView(ApiModel):
    account_id: int
    name: str
    screen: str
    node_id: int | None
    editing: bool
    seen_seconds_ago: float


class TeamView(ApiModel):
    role: UniverseRole | None
    permissions: list[Permission]
    canon_approval: bool
    present: list[PresentView]
    queued: int
    proposals: int
    revision: int
    world_busy: bool
    me: AuthorView | None
    heartbeat_seconds: int
    presence_ttl_seconds: float


class PresenceUpdate(ApiModel):
    screen: str = Field(max_length=PRESENCE_SCREEN_MAX_LENGTH)
    node_id: int | None = Field(default=None, ge=1)
    editing: bool = False


class QueuePage(ApiModel):
    items: list[QueuedActView]
    total: int


class ProposalPage(ApiModel):
    items: list[CanonProposalView]
    total: int


class ProposalDecision(ApiModel):
    note: str = Field(default="", max_length=TEAM_NOTE_MAX_LENGTH)


class SharedUpdate(ApiModel):
    shared: bool


class NodeRevisionView(ApiModel):
    node_id: int
    revision: int
    changed_by: str | None
    changed_at: datetime | None
