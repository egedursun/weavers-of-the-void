from aerona.db.tables.culture import ItemHistoryRow
from aerona.domain.enums.culture import ItemDeed
from aerona.engine.context import TickContext

NOTE_MAX = 480


def record(ctx: TickContext, item_id: int, deed: ItemDeed, actor: int | None, note: str) -> None:
    ctx.session.add(ItemHistoryRow(item_entity_id=item_id, epoch=ctx.epoch, deed=deed, actor_entity_id=actor, note=note[:NOTE_MAX]))
