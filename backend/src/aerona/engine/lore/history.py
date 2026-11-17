from aerona.db.record_context import current_scope
from aerona.db.tables.culture import ItemHistoryRow
from aerona.domain.enums.culture import ItemDeed
from aerona.engine.context import TickContext

NOTE_MAX = 480


def scope_incident() -> int | None:
    scope = current_scope()
    while scope is not None and scope.incident_id is None:
        scope = scope.parent
    return scope.incident_id if scope is not None else None


def record(ctx: TickContext, item_id: int, deed: ItemDeed, actor: int | None, note: str, *, incident_id: int | None = None) -> ItemHistoryRow:
    row = ItemHistoryRow(
        item_entity_id=item_id,
        epoch=ctx.epoch,
        deed=deed,
        actor_entity_id=actor,
        note=note[:NOTE_MAX],
        incident_id=incident_id if incident_id is not None else scope_incident(),
    )
    ctx.session.add(row)
    return row
