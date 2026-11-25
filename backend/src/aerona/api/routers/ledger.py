from datetime import datetime

from fastapi import APIRouter, Path, Query, status
from fastapi.responses import JSONResponse

from aerona.api.authors import LegacyAuthorDep, authored
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.team import AuthorView, QueuedActView
from aerona.api.views.team import author_view, queued_view
from aerona.constants.team import REASON_COLUMN_MAX_LENGTH
from aerona.core.act_note import ActNote, noting
from aerona.core.errors import NotFoundError
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.team import QueuedActSource
from aerona.services.accounts.guard import ensure_may_undo
from aerona.services.divine_will.player import UNDO_ACTION, UNDO_TITLE
from aerona.services.ledger import EpochCount, LedgerFilters, UndoResult, action_label
from aerona.services.team.execute import world_busy
from aerona.services.team.queue import QueueDraft, enqueue

router = APIRouter(tags=["ledger"])

NO_ENTRY = "No such entry in the ledger."


class LedgerEntry(ApiModel):
    id: int
    epoch: int
    actor_kind: ActorKind
    actor_node_id: int | None
    actor_name: str
    tool: str
    action_kind: ActionKind
    input_summary: str | None
    undone: bool
    undone_at: datetime | None
    applied: list[str]
    conflicts: list[str]
    created_at: datetime
    reason: str | None
    author: AuthorView | None
    undone_by: AuthorView | None


class LedgerEntryView(ApiModel):
    entry: LedgerEntry
    label: str
    change_count: int
    rows: list[str]
    dependents: list[int]


class LedgerPage(ApiModel):
    current_epoch: int
    epochs: list[EpochCount]
    entries: list[LedgerEntryView]


def entry_of(row: LedgerEntryRow, legacy: AuthorView | None) -> LedgerEntry:
    return LedgerEntry(
        id=row.id,
        epoch=row.epoch,
        actor_kind=row.actor_kind,
        actor_node_id=row.actor_node_id,
        actor_name=row.actor_name,
        tool=row.tool,
        action_kind=row.action_kind,
        input_summary=row.input_summary,
        undone=row.undone,
        undone_at=row.undone_at,
        applied=list(row.applied),
        conflicts=list(row.conflicts),
        created_at=row.created_at,
        reason=row.reason,
        author=authored(row.author_account_id, row.author_name, by_hand=row.actor_kind is ActorKind.CREATOR, legacy=legacy),
        undone_by=author_view(row.undone_by_account_id, row.undone_by_name),
    )


@router.get("/ledger", response_model=LedgerPage)
async def read_ledger(
    services: ServicesDep,
    legacy: LegacyAuthorDep,
    *,
    epoch: int | None = Query(default=None, ge=1),
    actor_kind: ActorKind | None = None,
    actor_id: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
    author_account_id: int | None = Query(default=None, ge=1),
    action_kind: ActionKind | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> LedgerPage:
    filters = LedgerFilters(author_account_id=author_account_id, action_kind=action_kind, since=since, until=until)
    async with reader(services) as session:
        rules = await world_rules(services, session)
        size = min(limit or rules.server.ledger_page_size, rules.server.ledger_page_max)
        view = await services.application.ledger.read(session, limit=size, epoch=epoch, actor_kind=actor_kind, actor_node_id=actor_id, filters=filters)
        return LedgerPage(
            current_epoch=view.current_epoch,
            epochs=view.epochs,
            entries=[
                LedgerEntryView(
                    entry=entry_of(item.entry, legacy),
                    label=action_label(item.entry.tool, item.entry.action_kind),
                    change_count=item.change_count,
                    rows=item.rows,
                    dependents=[dependent.id for dependent in item.dependents],
                )
                for item in view.entries
            ],
        )


@router.post("/ledger/{entry_id}/undo", response_model=UndoResult, responses={202: {"model": QueuedActView}})
async def undo(
    services: ServicesDep,
    legacy: LegacyAuthorDep,
    entry_id: int = Path(ge=1),
    reason: str | None = Query(default=None, max_length=REASON_COLUMN_MAX_LENGTH),
) -> UndoResult | JSONResponse:
    async with services.database.read() as session:
        entry = await session.get(LedgerEntryRow, entry_id)
    if entry is None:
        raise NotFoundError(NO_ENTRY)
    author = authored(entry.author_account_id, entry.author_name, by_hand=entry.actor_kind is ActorKind.CREATOR, legacy=legacy)
    ensure_may_undo(author.account_id if author is not None else None)
    note = ActNote(reason=reason.strip() if reason and reason.strip() else None)
    with noting(note):
        if world_busy(services):
            draft = QueueDraft(QueuedActSource.UNDO, UNDO_ACTION, UNDO_TITLE.format(entry_id=entry_id), {"entry_id": entry_id}, note.reason)
            queued = await enqueue(services, draft)
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=queued_view(queued).model_dump(mode="json"))
        async with services.database.write() as session:
            rules = await world_rules(services, session)
            return await services.application.ledger.undo(session, rules, entry_id, epoch_running=False)
