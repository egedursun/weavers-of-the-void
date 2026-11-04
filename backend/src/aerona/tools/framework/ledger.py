from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH
from aerona.core.action_text import ELLIPSIS, describe_arguments
from aerona.db.ledger_capture import LEDGER_TABLES, TURN_TABLES, ChangeCapture, LedgerDraft, RowChange, jsonable, write_entry
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind

TOOL_UNTRACKED = LEDGER_TABLES | TURN_TABLES


def change_capture(session: AsyncSession) -> ChangeCapture:
    capture = ChangeCapture(session, TOOL_UNTRACKED)
    capture.start()
    return capture


def summarize(arguments: dict[str, Any]) -> str:
    text = describe_arguments(jsonable(arguments))
    return text if len(text) <= LEDGER_SUMMARY_MAX_LENGTH else text[: LEDGER_SUMMARY_MAX_LENGTH - 1].rstrip() + ELLIPSIS


@dataclass(frozen=True)
class ActionEntry:
    epoch: int
    actor_kind: ActorKind
    actor_node_id: int
    actor_name: str
    tool: str
    action_kind: ActionKind
    summary: str
    target_node_id: int | None
    essence_spent: int
    detail: str | None


async def record_action(session: AsyncSession, entry: ActionEntry, changes: list[RowChange]) -> LedgerEntryRow:
    draft = LedgerDraft(
        epoch=entry.epoch,
        actor_kind=entry.actor_kind,
        actor_node_id=entry.actor_node_id,
        actor_name=entry.actor_name,
        tool=entry.tool,
        action_kind=entry.action_kind,
        input_summary=entry.summary,
    )
    ledger = await write_entry(session, draft, changes)
    session.add(
        ActionRecordRow(
            epoch=entry.epoch,
            actor_kind=entry.actor_kind,
            actor_node_id=entry.actor_node_id,
            kind=entry.action_kind,
            target_node_id=entry.target_node_id,
            ledger_entry_id=ledger.id,
            essence_spent=entry.essence_spent,
            summary=entry.summary,
            detail=entry.detail,
        )
    )
    await session.flush()
    return ledger
