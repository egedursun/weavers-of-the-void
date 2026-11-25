from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH, QUEUED_TEXT
from aerona.core.account_scope import AccountRef, acting_account
from aerona.core.act_note import current_note
from aerona.db.tables.team import CanonProposalRow, QueuedActRow
from aerona.domain.enums.team import ProposalStatus, QueuedActSource
from aerona.services.container import Services
from aerona.services.player.catalog import ActionSpec
from aerona.services.player.scope import ActionOutcome
from aerona.services.team.canon import rehearse
from aerona.services.team.execute import canon_gated, plan_step, run_lever, world_busy
from aerona.services.team.proposals import approve, author_of, pending_row, proposal_event, propose
from aerona.services.team.queue import QueueDraft, enqueue


@dataclass(frozen=True)
class Admitted:
    queued: QueuedActRow | None = None
    proposal: CanonProposalRow | None = None
    outcome: ActionOutcome | None = None


async def queue_lever(services: Services, spec: ActionSpec, payload: Mapping[str, Any], source: QueuedActSource) -> QueuedActRow:
    step = plan_step()
    draft = QueueDraft(
        source,
        spec.id,
        spec.title,
        payload,
        current_note().reason,
        expected_revision=current_note().expected_revision,
        plan_id=step[0] if step is not None else None,
        plan_ordinal=step[1] if step is not None else None,
    )
    return await enqueue(services, draft)


async def admit(services: Services, spec: ActionSpec, payload: Mapping[str, Any], source: QueuedActSource = QueuedActSource.LEVER) -> Admitted:
    if world_busy(services):
        return Admitted(queued=await queue_lever(services, spec, payload, source))
    if canon_gated():
        reading = await rehearse(services, spec, payload)
        if reading.locked:
            return Admitted(proposal=await propose(services, spec, payload, current_note().reason, reading))
    return Admitted(outcome=await run_lever(services, spec, payload))


async def approve_now_or_later(services: Services, proposal_id: int, by: AccountRef | None, note: str) -> CanonProposalRow:
    if not world_busy(services):
        return await approve(services, proposal_id, by, note)
    async with services.database.write() as session:
        row = await pending_row(session, proposal_id)
        row.status = ProposalStatus.APPROVED
        row.decided_at = datetime.now(UTC)
        row.decided_by_account_id = by.id if by is not None else None
        row.decided_by_name = by.name[:AUTHOR_NAME_MAX_LENGTH] if by is not None else None
        row.note = note
        row.result = QUEUED_TEXT
    with acting_account(author_of(row)):
        await enqueue(services, QueueDraft(QueuedActSource.LEVER, row.action_id, row.title, row.payload, row.reason, approved_proposal_id=row.id))
    proposal_event(services, row)
    return row
