import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH, PROPOSED_TEXT
from aerona.core.account_scope import AccountRef, acting_account
from aerona.core.act_note import ActNote, noting
from aerona.core.errors import AeronaError, ConflictError, EditConflictError, ForbiddenError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.divine_will import DivineWillPlanStepRow
from aerona.db.tables.team import QueuedActRow
from aerona.domain.enums.accounts import Permission
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.divine_will import StepStatus
from aerona.domain.enums.team import QueuedActSource, QueuedActStatus
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.kinds import EventKind
from aerona.services.accounts.guard import ensure_allowed, ensure_lever_allowed, ensure_may_undo, enter_grant
from aerona.services.container import Services
from aerona.services.notifications import NotificationRequest
from aerona.services.player.catalog import action
from aerona.services.presence.replay import replay_tool
from aerona.services.rule_changes import rule_desk
from aerona.services.team.canon import rehearse
from aerona.services.team.execute import author_grant, canon_gated, rules_in, run_lever, settle_plan_step, world_busy
from aerona.services.team.proposals import propose

LOGGER = logging.getLogger(__name__)
NOT_QUEUED = "That act is no longer waiting in the queue."
NO_SUCH_ACT = "There is no such queued act."
NOT_YOURS = "This act is {author}'s; only its author or an administrator can change it."
NOT_FAILED = "Only an act that failed can be tried again."
SOMEONE = "Someone"
APPLIED_TEXT = "Applied after the age ended."
KEY_SEPARATOR = "."
FAILED_TITLE = "A queued act could not be applied"


@dataclass(frozen=True)
class QueueDraft:
    source: QueuedActSource
    action_id: str
    title: str
    payload: Mapping[str, Any]
    reason: str | None = None
    expected_revision: int | None = None
    speaker_node_id: int | None = None
    presence_session_id: int | None = None
    plan_id: int | None = None
    plan_ordinal: int | None = None
    approved_proposal_id: int | None = None


def author_of(row: QueuedActRow) -> AccountRef | None:
    if row.author_account_id is None:
        return None
    return AccountRef(row.author_account_id, row.author_name or "")


def queue_event(services: Services, row: QueuedActRow) -> None:
    services.bus.publish(
        EventKind.TEAM_QUEUE_CHANGED,
        {"id": row.id, "status": row.status.value, "action_id": row.action_id, "author_name": row.author_name, "result": row.result},
    )


async def enqueue(services: Services, draft: QueueDraft) -> QueuedActRow:
    async with services.database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        row = QueuedActRow(
            source=draft.source,
            action_id=draft.action_id,
            title=draft.title,
            payload=dict(draft.payload),
            reason=draft.reason,
            expected_revision=draft.expected_revision,
            speaker_node_id=draft.speaker_node_id,
            presence_session_id=draft.presence_session_id,
            plan_id=draft.plan_id,
            plan_ordinal=draft.plan_ordinal,
            proposal_id=draft.approved_proposal_id,
            queued_epoch=cosmos.epoch,
        )
        session.add(row)
        await session.flush()
        if draft.plan_id is not None and draft.plan_ordinal is not None:
            step = await session.get(DivineWillPlanStepRow, (draft.plan_id, draft.plan_ordinal))
            if step is not None:
                step.status = StepStatus.RUNNING
                step.result_text = row.title
    queue_event(services, row)
    return row


async def waiting_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(QueuedActRow).where(QueuedActRow.status == QueuedActStatus.QUEUED)) or 0)


async def owned_failure(services: Services, act_id: int, by: AccountRef | None, admin: bool, wanted: QueuedActStatus) -> QueuedActRow:
    async with services.database.read() as session:
        row = await session.get(QueuedActRow, act_id)
    if row is None:
        raise NotFoundError(NO_SUCH_ACT)
    mine = by is not None and row.author_account_id == by.id
    if not (mine or admin or by is None):
        raise ForbiddenError(NOT_YOURS.format(author=row.author_name or SOMEONE))
    if row.status is not wanted:
        raise ConflictError(NOT_QUEUED if wanted is QueuedActStatus.QUEUED else NOT_FAILED)
    return row


async def cancel(services: Services, act_id: int, by: AccountRef | None, admin: bool) -> QueuedActRow:
    await owned_failure(services, act_id, by, admin, QueuedActStatus.QUEUED)
    async with services.database.write() as session:
        row = await session.get(QueuedActRow, act_id)
        if row is None or row.status is not QueuedActStatus.QUEUED:
            raise ConflictError(NOT_QUEUED)
        row.status = QueuedActStatus.CANCELLED
        row.applied_at = datetime.now(UTC)
        row.cancelled_by_account_id = by.id if by is not None else None
        row.cancelled_by_name = by.name[:AUTHOR_NAME_MAX_LENGTH] if by is not None else None
    queue_event(services, row)
    return row


async def retry(services: Services, act_id: int, by: AccountRef | None, admin: bool) -> QueuedActRow:
    await owned_failure(services, act_id, by, admin, QueuedActStatus.FAILED)
    async with services.database.write() as session:
        row = await session.get(QueuedActRow, act_id)
        if row is None:
            raise NotFoundError(NO_SUCH_ACT)
        row.status = QueuedActStatus.QUEUED
        row.expected_revision = None
        row.conflict = []
        row.result = ""
        row.applied_at = None
    queue_event(services, row)
    if not world_busy(services):
        await apply_queue(services)
    async with services.database.read() as session:
        found = await session.get(QueuedActRow, act_id)
    return found or row


async def apply_rules(services: Services, payload: Mapping[str, Any]) -> str:
    changes = payload.get("changes") or {}
    parsed: list[tuple[str, str, float | None]] = []
    for path, value in dict(changes).items():
        namespace, _separator, key = str(path).partition(KEY_SEPARATOR)
        parsed.append((namespace, key, None if value is None else float(value)))
    await services.rules.apply_batch(parsed, reset_all=bool(payload.get("reset_all")))
    await rule_desk(services).settle({})
    return APPLIED_TEXT


async def apply_undo(services: Services, payload: Mapping[str, Any]) -> tuple[str, int | None]:
    entry_id = int(payload["entry_id"])
    async with services.database.write() as session:
        rules = await rules_in(services, session)
        result = await services.application.ledger.undo(session, rules, entry_id, epoch_running=False)
    return APPLIED_TEXT, result.entry_id


async def enter_author_grant(services: Services, author: AccountRef | None) -> None:
    grant = await author_grant(services, author)
    if grant is not None:
        enter_grant(grant)


def require_permission(row: QueuedActRow) -> None:
    if row.source is QueuedActSource.RULES:
        ensure_allowed(Permission.CHANGE_RULES)
    elif row.source is QueuedActSource.UNDO:
        ensure_may_undo(row.author_account_id)
    elif row.source is QueuedActSource.PRESENCE:
        ensure_allowed(Permission.PRESENCE_ON_RECORD)
    else:
        ensure_lever_allowed(row.action_id)


@dataclass(frozen=True)
class Applied:
    status: QueuedActStatus
    text: str
    entry_id: int | None = None
    proposal_id: int | None = None


async def applied(services: Services, row: QueuedActRow) -> Applied:
    await enter_author_grant(services, author_of(row))
    require_permission(row)
    if row.source is QueuedActSource.RULES:
        return Applied(QueuedActStatus.APPLIED, await apply_rules(services, row.payload))
    if row.source is QueuedActSource.UNDO:
        text, entry_id = await apply_undo(services, row.payload)
        return Applied(QueuedActStatus.APPLIED, text, entry_id)
    if row.source is QueuedActSource.PRESENCE:
        return Applied(QueuedActStatus.APPLIED, await replay_tool(services, row))
    spec = action(row.action_id)
    if canon_gated() and row.proposal_id is None:
        reading = await rehearse(services, spec, row.payload)
        if reading.locked:
            proposal = await propose(services, spec, row.payload, row.reason, reading)
            return Applied(QueuedActStatus.PROPOSED, PROPOSED_TEXT, proposal_id=proposal.id)
    outcome = await run_lever(services, spec, row.payload)
    return Applied(QueuedActStatus.APPLIED, outcome.message or APPLIED_TEXT, outcome.ledger_entry_id)


async def tell_author(services: Services, session: AsyncSession, row: QueuedActRow) -> None:
    rules = await rules_in(services, session)
    created = await services.application.notifier.notify(
        session,
        rules,
        NotificationRequest(category=NotificationCategory.WORK, title=FAILED_TITLE, body=f"{row.title}: {row.result}", forced=True),
    )
    if created is not None:
        created.recipient_account_id = row.author_account_id


async def apply_one(services: Services, row: QueuedActRow) -> None:
    conflict: list[dict[str, object]] = []
    try:
        with acting_account(author_of(row)), noting(ActNote(reason=row.reason, expected_revision=row.expected_revision)):
            done = await applied(services, row)
    except EditConflictError as error:
        conflict = error.changes
        done = Applied(QueuedActStatus.FAILED, error.message)
    except AeronaError as error:
        done = Applied(QueuedActStatus.FAILED, error.message)
    except Exception as error:
        LOGGER.exception("Queued act %s failed", row.id)
        done = Applied(QueuedActStatus.FAILED, str(error) or type(error).__name__)
    async with services.database.write() as session:
        stored = await session.get(QueuedActRow, row.id)
        if stored is None:
            return
        stored.status = done.status
        stored.result = done.text
        stored.applied_at = datetime.now(UTC)
        stored.ledger_entry_id = done.entry_id
        stored.proposal_id = done.proposal_id
        stored.conflict = list(conflict)
        if done.status is not QueuedActStatus.PROPOSED:
            ok = done.status is QueuedActStatus.APPLIED
            await settle_plan_step(session, stored.plan_id, stored.plan_ordinal, ok=ok, text=done.text, entry_id=done.entry_id)
        if done.status is QueuedActStatus.FAILED:
            await tell_author(services, session, stored)
        row = stored
    queue_event(services, row)


async def apply_queue(services: Services) -> int:
    count = 0
    async with services.team.applying:
        while not world_busy(services):
            async with services.database.read() as session:
                found = await session.scalar(select(QueuedActRow).where(QueuedActRow.status == QueuedActStatus.QUEUED).order_by(QueuedActRow.id).limit(1))
            if found is None:
                return count
            await apply_one(services, found)
            count += 1
    return count


async def released(services: Services, group: str) -> None:
    if group == WORLD_GROUP:
        await apply_queue(services)


def bind_team(services: Services) -> None:
    async def hook(group: str) -> None:
        await released(services, group)

    services.jobs.on_group_released(hook)
