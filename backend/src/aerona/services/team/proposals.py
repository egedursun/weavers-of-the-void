from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH
from aerona.core.account_scope import AccountRef, acting_account
from aerona.core.act_note import ActNote, noting
from aerona.core.errors import ConflictError, ForbiddenError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.team import CanonProposalRow
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.team import ProposalStatus
from aerona.events.kinds import EventKind
from aerona.services.accounts.guard import CURRENT_GRANT, ensure_lever_allowed
from aerona.services.container import Services
from aerona.services.notifications import NotificationRequest
from aerona.services.player.catalog import ActionSpec, action
from aerona.services.player.scope import ActionOutcome
from aerona.services.team.canon import CanonReading
from aerona.services.team.execute import author_grant, plan_step, rules_in, run_lever, settle_plan_step

NO_SUCH_PROPOSAL = "There is no such proposal."
DECIDED = "That proposal was already decided."
NOT_AUTHOR = "Only its author can withdraw a proposal."
PROPOSED_TITLE = "A change to locked canon waits for approval"
APPROVED_TITLE = "Your proposal was approved"
REJECTED_TITLE = "Your proposal was rejected"
NOT_APPROVED = "The change was not approved."


def proposal_event(services: Services, row: CanonProposalRow) -> None:
    services.bus.publish(
        EventKind.TEAM_PROPOSAL_CHANGED,
        {"id": row.id, "status": row.status.value, "action_id": row.action_id, "author_name": row.author_name, "decided_by_name": row.decided_by_name},
    )


async def tell(services: Services, session: AsyncSession, title: str, body: str, recipient: int | None) -> None:
    rules = await rules_in(services, session)
    created = await services.application.notifier.notify(
        session, rules, NotificationRequest(category=NotificationCategory.WORK, title=title, body=body, forced=True)
    )
    if created is not None:
        created.recipient_account_id = recipient


async def propose(services: Services, spec: ActionSpec, payload: Mapping[str, Any], reason: str | None, reading: CanonReading) -> CanonProposalRow:
    step = plan_step()
    async with services.database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        row = CanonProposalRow(
            action_id=spec.id,
            title=spec.title,
            payload=dict(payload),
            reason=reason,
            preview=reading.preview,
            touches=[touch.value for touch in reading.touches],
            held_node_ids=list(reading.held_node_ids),
            proposed_epoch=cosmos.epoch,
            plan_id=step[0] if step is not None else None,
            plan_ordinal=step[1] if step is not None else None,
        )
        session.add(row)
        await session.flush()
        await tell(services, session, PROPOSED_TITLE, f"{row.author_name or ''}: {row.title}".strip(": "), None)
    proposal_event(services, row)
    return row


def author_of(row: CanonProposalRow) -> AccountRef | None:
    return AccountRef(row.author_account_id, row.author_name or "") if row.author_account_id is not None else None


async def pending_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(CanonProposalRow).where(CanonProposalRow.status == ProposalStatus.PENDING)) or 0)


async def pending_row(session: AsyncSession, proposal_id: int) -> CanonProposalRow:
    row = await session.get(CanonProposalRow, proposal_id)
    if row is None:
        raise NotFoundError(NO_SUCH_PROPOSAL)
    if row.status is not ProposalStatus.PENDING:
        raise ConflictError(DECIDED)
    return row


async def decided(
    services: Services, proposal_id: int, status: ProposalStatus, by: AccountRef | None, *, note: str, outcome: ActionOutcome | None
) -> CanonProposalRow:
    async with services.database.write() as session:
        row = await pending_row(session, proposal_id)
        row.status = status
        row.decided_at = datetime.now(UTC)
        row.decided_by_account_id = by.id if by is not None else None
        row.decided_by_name = by.name[:AUTHOR_NAME_MAX_LENGTH] if by is not None else None
        row.note = note
        if outcome is not None:
            row.result = outcome.message
            row.ledger_entry_id = outcome.ledger_entry_id
        ok = status is ProposalStatus.APPROVED
        await settle_plan_step(session, row.plan_id, row.plan_ordinal, ok=ok, text=row.result if ok else (note or NOT_APPROVED), entry_id=row.ledger_entry_id)
        if status is not ProposalStatus.WITHDRAWN:
            title = APPROVED_TITLE if status is ProposalStatus.APPROVED else REJECTED_TITLE
            await tell(services, session, title, f"{row.title}{': ' + note if note else ''}", row.author_account_id)
    proposal_event(services, row)
    return row


async def approve(services: Services, proposal_id: int, by: AccountRef | None, note: str) -> CanonProposalRow:
    async with services.database.read() as session:
        row = await pending_row(session, proposal_id)
    author = author_of(row)
    grant = await author_grant(services, author)
    token = CURRENT_GRANT.set(grant) if grant is not None else None
    try:
        with acting_account(author), noting(ActNote(reason=row.reason)):
            ensure_lever_allowed(row.action_id)
            outcome = await run_lever(services, action(row.action_id), row.payload)
    finally:
        if token is not None:
            CURRENT_GRANT.reset(token)
    return await decided(services, proposal_id, ProposalStatus.APPROVED, by, note=note, outcome=outcome)


async def reject(services: Services, proposal_id: int, by: AccountRef | None, note: str) -> CanonProposalRow:
    return await decided(services, proposal_id, ProposalStatus.REJECTED, by, note=note, outcome=None)


async def withdraw(services: Services, proposal_id: int, by: AccountRef | None) -> CanonProposalRow:
    async with services.database.read() as session:
        row = await pending_row(session, proposal_id)
    if by is not None and row.author_account_id != by.id:
        raise ForbiddenError(NOT_AUTHOR)
    return await decided(services, proposal_id, ProposalStatus.WITHDRAWN, by, note="", outcome=None)
