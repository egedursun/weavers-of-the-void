from typing import Any

from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.team import CanonProposalView, QueuedActView
from aerona.domain.enums.accounts import Permission
from aerona.services.player.catalog import ActionGroup, ActionMode

ActionValue = int | float | str | bool | None


class ActionResponse(ApiModel):
    action: str
    message: str
    essence_spent: int = 0
    essence_gained: int = 0
    target_node_id: int | None = None
    created_ids: list[int] = Field(default_factory=list)
    ledger_entry_id: int | None = None
    values: dict[str, ActionValue] = Field(default_factory=dict)
    job_id: str | None = None
    queued: QueuedActView | None = None
    proposal: CanonProposalView | None = None


class ActionCatalogueItem(ApiModel):
    id: str
    title: str
    group: ActionGroup
    mode: ActionMode
    cost: str
    confirmation: str | None
    rows: list[str]
    path: str
    permission: Permission
    hold_fields: list[str]
    method: str
    input_schema: dict[str, Any]
