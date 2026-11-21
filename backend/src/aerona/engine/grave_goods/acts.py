from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.grave_goods.robbery import MAGICAL, magic_at
from aerona.engine.lore import items
from aerona.engine.recording.record import record


async def guard_allowed(ctx: TickContext, row: GraveGoodsRow, guard: GraveGuard, place_id: int | None) -> bool:
    return guard not in MAGICAL or await magic_at(ctx, place_id) > 0


async def set_guard(ctx: TickContext, row: GraveGoodsRow, guard: GraveGuard, actor: int | None, place_id: int | None) -> None:
    row.guard = guard
    roles = {IncidentRole.ACTOR: actor, IncidentRole.SUBJECT: row.dead_entity_id, IncidentRole.PLACE: row.grave_entity_id}
    await record(ctx, "dead.grave_guarded", roles=roles, facts={"guard": guard}, place=place_id)


async def lay_goods(ctx: TickContext, row: GraveGoodsRow, dead: EntityRow, laid: list[EntityRow]) -> None:
    for item in laid:
        await items.give(ctx, item, dead.id, ItemDeed.BURIAL, f"laid with {dead.name} in the grave")
    row.items = sorted({*(row.items or []), *(item.id for item in laid)})
    roles = {IncidentRole.SUBJECT: dead.id, IncidentRole.PLACE: row.grave_entity_id, IncidentRole.INSTRUMENT: [item.id for item in laid]}
    await record(ctx, "dead.goods_placed", roles=roles, facts={"items": len(laid), "value": row.goods_value, "guard": row.guard}, place=dead.location_id)
