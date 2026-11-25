from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.divine_will import active_session, add_event, next_cycle_ordinal
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillConfirmationRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import AttachmentKind, ConfirmationStatus, CycleEventKind, CycleNotice, CycleStatus, DivineWillMode
from aerona.llm.content import ModelCapabilities

INTERRUPTED_TEXT = "The exchange stopped when the server was restarted before it finished."
EXPIRED_DECISION = "expired"
UNSEEN_PICTURE = "The model cannot see pictures here, so this picture was kept but not shown to it."
UNSHOWN_FORMAT = "This picture's format cannot be shown to the model, so it was kept but not shown to it."
PICTURE_TYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
VISION_NOTICE = CycleNotice.VISION_UNAVAILABLE.value
STEP_LIMIT_NOTICE = CycleNotice.STEP_LIMIT.value


def now() -> datetime:
    return datetime.now(UTC)


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


async def open_session(session: AsyncSession, epoch: int) -> DivineWillSessionRow:
    found = await active_session(session)
    if found is not None:
        return found
    row = DivineWillSessionRow(opened_epoch=epoch)
    session.add(row)
    await session.flush()
    return row


async def expire_waiting(session: AsyncSession, cycle: DivineWillCycleRow) -> None:
    pending = await session.scalars(
        select(DivineWillConfirmationRow)
        .where(DivineWillConfirmationRow.cycle_id == cycle.id, DivineWillConfirmationRow.status == ConfirmationStatus.PENDING)
        .order_by(DivineWillConfirmationRow.id)
    )
    for row in pending:
        row.status = ConfirmationStatus.EXPIRED
        row.decided_at = now()
        await add_event(session, cycle.id, CycleEventKind.CONFIRMATION_REPLY, payload={"confirmation_id": row.id, "decision": EXPIRED_DECISION})


async def end_cycle(session: AsyncSession, cycle: DivineWillCycleRow, status: CycleStatus, error: str = "") -> None:
    await expire_waiting(session, cycle)
    cycle.status = status
    cycle.finished_at = now()
    if error:
        cycle.error = error


async def settle_stale(session: AsyncSession, session_id: int) -> list[DivineWillCycleRow]:
    open_cycles = await session.scalars(
        select(DivineWillCycleRow)
        .where(DivineWillCycleRow.session_id == session_id, DivineWillCycleRow.status.in_([CycleStatus.RUNNING, CycleStatus.AWAITING_CONFIRMATION]))
        .order_by(DivineWillCycleRow.ordinal)
    )
    settled: list[DivineWillCycleRow] = []
    for cycle in open_cycles:
        if cycle.status is CycleStatus.RUNNING:
            await add_event(session, cycle.id, CycleEventKind.ERROR, payload={"text": INTERRUPTED_TEXT})
            await end_cycle(session, cycle, CycleStatus.FAILED, INTERRUPTED_TEXT)
        else:
            await end_cycle(session, cycle, CycleStatus.DONE)
        settled.append(cycle)
    return settled


async def close_session(session: AsyncSession, row: DivineWillSessionRow, epoch: int) -> list[DivineWillCycleRow]:
    open_cycles = await session.scalars(
        select(DivineWillCycleRow)
        .where(DivineWillCycleRow.session_id == row.id, DivineWillCycleRow.status.in_([CycleStatus.RUNNING, CycleStatus.AWAITING_CONFIRMATION]))
        .order_by(DivineWillCycleRow.ordinal)
    )
    closed = list(open_cycles)
    for cycle in closed:
        await end_cycle(session, cycle, CycleStatus.CANCELLED)
    row.closed_at = now()
    row.closed_epoch = epoch
    return closed


async def bind_attachments(session: AsyncSession, cycle_id: int, attachment_ids: Sequence[int], limit: int) -> list[DivineWillAttachmentRow]:
    wanted = list(dict.fromkeys(attachment_ids))
    if len(wanted) > limit:
        raise ValidationFailedError(f"At most {several(limit, 'file', 'files')} can go with one request.")
    if not wanted:
        return []
    rows = list(await session.scalars(select(DivineWillAttachmentRow).where(DivineWillAttachmentRow.id.in_(wanted)).order_by(DivineWillAttachmentRow.id)))
    missing = sorted(set(wanted) - {row.id for row in rows})
    if missing:
        raise ValidationFailedError(f"No such attachment: {', '.join(str(item) for item in missing)}.")
    taken = [row.id for row in rows if row.cycle_id is not None and row.cycle_id != cycle_id]
    if taken:
        raise ValidationFailedError(f"These attachments already belong to another request: {', '.join(str(item) for item in taken)}.")
    for row in rows:
        row.cycle_id = cycle_id
    return rows


async def new_cycle(session: AsyncSession, holder: DivineWillSessionRow, *, mode: DivineWillMode, epoch: int, text: str, model: str) -> DivineWillCycleRow:
    ordinal = await next_cycle_ordinal(session, holder.id)
    if not holder.title:
        holder.title = first_line(text)
    cycle = DivineWillCycleRow(session_id=holder.id, ordinal=ordinal, mode=mode, epoch=epoch, status=CycleStatus.RUNNING, player_text=text, model=model)
    session.add(cycle)
    await session.flush()
    return cycle


async def judge_pictures(session: AsyncSession, cycle_id: int, capabilities: ModelCapabilities) -> tuple[list[DivineWillAttachmentRow], bool]:
    rows = list(
        await session.scalars(
            select(DivineWillAttachmentRow)
            .where(DivineWillAttachmentRow.cycle_id == cycle_id, DivineWillAttachmentRow.kind == AttachmentKind.IMAGE)
            .order_by(DivineWillAttachmentRow.id)
        )
    )
    shown: list[DivineWillAttachmentRow] = []
    newly_unseen = False
    for row in rows:
        if capabilities.images and row.mime in PICTURE_TYPES:
            row.seen_by_model = True
            shown.append(row)
            continue
        note = UNSEEN_PICTURE if not capabilities.images else UNSHOWN_FORMAT
        if row.note != note or row.seen_by_model:
            newly_unseen = True
        row.seen_by_model = False
        row.note = note
    return shown, newly_unseen
