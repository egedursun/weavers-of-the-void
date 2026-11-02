from datetime import datetime

from fastapi import APIRouter, Path, Query

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.services.ledger import EpochCount, UndoResult, action_label

router = APIRouter(tags=["ledger"])


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


@router.get("/ledger", response_model=LedgerPage)
async def read_ledger(
    services: ServicesDep,
    epoch: int | None = Query(default=None, ge=1),
    actor_kind: ActorKind | None = None,
    actor_id: int | None = Query(default=None, ge=1),
    limit: int | None = Query(default=None, ge=1),
) -> LedgerPage:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        size = min(limit or rules.server.ledger_page_size, rules.server.ledger_page_max)
        view = await services.application.ledger.read(session, limit=size, epoch=epoch, actor_kind=actor_kind, actor_node_id=actor_id)
        return LedgerPage(
            current_epoch=view.current_epoch,
            epochs=view.epochs,
            entries=[
                LedgerEntryView(
                    entry=LedgerEntry.model_validate(item.entry),
                    label=action_label(item.entry.tool, item.entry.action_kind),
                    change_count=item.change_count,
                    rows=item.rows,
                    dependents=[dependent.id for dependent in item.dependents],
                )
                for item in view.entries
            ],
        )


@router.post("/ledger/{entry_id}/undo", response_model=UndoResult)
async def undo(services: ServicesDep, entry_id: int = Path(ge=1)) -> UndoResult:
    running = services.jobs.busy_group(WORLD_GROUP) is not None
    async with services.database.write() as session:
        rules = await world_rules(services, session)
        return await services.application.ledger.undo(session, rules, entry_id, epoch_running=running)
