from math import ceil

from sqlalchemy import select

from aerona.catalog.death_shapes import GROUND_REMAINS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.death_work.handling import own_treatment
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.lore.history import record as record_deed
from aerona.engine.mortal.standing import standing_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.recording.record import record


async def tomb_at(ctx: TickContext, place_id: int) -> int | None:
    tomb = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.kind == StructureKind.TOMB, StructureProfileRow.host_entity_id == place_id)
    return await ctx.session.scalar(tomb.order_by(StructureProfileRow.structure_entity_id).limit(1))


async def custom_of(ctx: TickContext, dead: EntityRow) -> RemainsTreatment | None:
    own = await own_treatment(ctx.session, dead)
    if own is not None:
        return own
    people = await people_of(ctx.session, dead)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.remains_treatment if culture is not None else None


async def share_of(ctx: TickContext, dead: EntityRow) -> float:
    renown = await standing_of(ctx.session, dead, "renown") or 0
    return min(PERCENT, ctx.rules.grave_goods.share_by_rank_pct * (PERCENT + renown) / PERCENT)


async def chosen_items(ctx: TickContext, dead: EntityRow, share: float) -> list[int]:
    owned = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.OWNS], sources=[dead.id])]
    profiles = {row.item_entity_id: row.renown for row in await ctx.session.scalars(select(ItemProfileRow).where(ItemProfileRow.item_entity_id.in_(owned)))}
    ranked = sorted(profiles, key=lambda item: (-profiles[item], item))
    return ranked[: ceil(len(ranked) * share / PERCENT)] if share > 0 else []


async def furnish_grave(ctx: TickContext, dead: EntityRow) -> GraveGoodsRow | None:
    if dead.location_id is None or held(dead.id):
        return None
    existing = await ctx.session.scalar(select(GraveGoodsRow).where(GraveGoodsRow.dead_entity_id == dead.id))
    if existing is not None:
        return existing
    custom = await custom_of(ctx, dead)
    if custom not in GROUND_REMAINS:
        return None
    share = await share_of(ctx, dead)
    kept = await chosen_items(ctx, dead, share)
    value = round_half_up(await points_of(ctx.session, dead) * share / PERCENT)
    if not kept and value <= 0:
        return None
    await shift_points(ctx.session, dead, -value)
    grave = await tomb_at(ctx, dead.location_id) or dead.location_id
    guard = GraveGuard.SEALED if value >= ctx.rules.grave_goods.sealed_value else GraveGuard.NONE
    row = GraveGoodsRow(
        dead_entity_id=dead.id, grave_entity_id=grave, custom=custom, items=kept, goods_value=value, guard=guard, placed_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    for item in kept:
        record_deed(ctx, item, ItemDeed.BURIAL, dead.id, f"laid with {dead.name} in the grave")
    await record(
        ctx,
        "dead.goods_placed",
        roles={IncidentRole.SUBJECT: dead.id, IncidentRole.PLACE: grave, IncidentRole.INSTRUMENT: kept},
        facts={"items": len(kept), "value": value, "guard": guard},
        place=dead.location_id,
    )
    return row
