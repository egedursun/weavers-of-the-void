from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import (
    MaterialBook,
    MaterialProps,
    armour_protection,
    heat_attrition,
    march_drag,
    node_material,
    set_node_material,
    weapon_damage,
)
from aerona.engine.economy.stocks import goods_of, holding, lots_of
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.military.units import resize
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat

THOUSAND = 1000


@dataclass(frozen=True)
class Kit:
    bonus: int
    weapons: MaterialKind | None
    armour: MaterialKind | None


async def _issue(ctx: TickContext, community: EntityRow, commodity: CommodityKind, wanted: int) -> tuple[int, MaterialKind | None, int]:
    lots = sorted((row for row in await lots_of(ctx.session, community.id, commodity) if row.quantity > 0), key=lambda row: (-row.quality, row.id))
    if not lots:
        return 0, None, 0
    best = lots[0]
    taken = await goods_of(ctx.session, ctx.epoch).take(community.id, commodity, wanted, GoodsFlow.WAR, material=best.material)
    return sum(lot.quantity for lot in taken), best.material, best.quality


async def equip_army(ctx: TickContext, community: EntityRow, army: EntityRow, size: int) -> Kit:
    table = ctx.rules.materials
    wanted = max(1, round_half_up(size / table.soldiers_per_kit))
    book = await MaterialBook.load(ctx.session)
    weapons, weapon_material, weapon_quality = await _issue(ctx, community, CommodityKind.WEAPONS, wanted)
    armour, armour_material, armour_quality = await _issue(ctx, community, CommodityKind.ARMOUR, wanted)
    score = 0.0
    if weapon_material is not None:
        props = book.props(community.world_id, weapon_material)
        if props is not None:
            score += weapon_damage(ctx.rules, props, weapon_quality) * min(1.0, weapons / wanted)
            await set_node_material(ctx.session, army.id, MaterialSlot.WEAPONS, weapon_material)
    if armour_material is not None:
        props = book.props(community.world_id, armour_material)
        if props is not None:
            score += armour_protection(ctx.rules, props, armour_quality) * min(1.0, armour / wanted)
            await set_node_material(ctx.session, army.id, MaterialSlot.ARMOUR, armour_material)
    return Kit(round_half_up(score * table.kit_equipment_pct / PERCENT), weapon_material, armour_material)


async def armour_of(ctx: TickContext, army: EntityRow) -> MaterialProps | None:
    row = await node_material(ctx.session, army.id, MaterialSlot.ARMOUR)
    if row is None:
        return None
    return (await MaterialBook.load(ctx.session)).props(army.world_id, row.material, row.world_material_id)


async def march_burden(ctx: TickContext, army: EntityRow) -> int:
    props = await armour_of(ctx, army)
    return march_drag(ctx.rules, props) if props is not None else 0


async def suffer_heat(ctx: TickContext, army: EntityRow, temperature: int) -> int:
    props = await armour_of(ctx, army)
    size = stat(army, "size")
    if props is None or size is None:
        return 0
    lost = round_half_up(size * heat_attrition(ctx.rules, props, temperature) / THOUSAND)
    if lost <= 0:
        return 0
    with flowing(FlowCategory.CASUALTY):
        await resize(ctx.session, ctx.rules, army, max(0, size - lost))
    return lost


async def siege_engines(ctx: TickContext, community: EntityRow | None, army: EntityRow) -> float:
    if community is None:
        return 0.0
    wanted = max(1, round_half_up((stat(army, "size") or 0) / ctx.rules.materials.soldiers_per_engine))
    held = await holding(ctx.session, community.id, CommodityKind.SIEGE_MATERIEL)
    if held <= 0:
        return 0.0
    used = await goods_of(ctx.session, ctx.epoch).take_units(community.id, CommodityKind.SIEGE_MATERIEL, min(held, wanted), GoodsFlow.SIEGE)
    return clamp_int(used * PERCENT / wanted, 0, PERCENT) / PERCENT


async def weapon_of(session: AsyncSession, node_id: int | None) -> MaterialProps | None:
    if node_id is None:
        return None
    row = await node_material(session, node_id, MaterialSlot.WEAPONS) or await node_material(session, node_id, MaterialSlot.BODY)
    if row is None:
        statement = (
            select(NodeMaterialRow)
            .join(BondRow, BondRow.target_node_id == NodeMaterialRow.node_id)
            .join(EntityRow, EntityRow.id == NodeMaterialRow.node_id)
            .where(
                BondRow.source_node_id == node_id,
                BondRow.kind == BondKind.OWNS,
                BondRow.state == BondState.ACTIVE,
                EntityRow.entity_type == EntityType.ITEM,
                EntityRow.status == EntityStatus.CANON,
                NodeMaterialRow.slot == MaterialSlot.BODY,
            )
            .order_by(NodeMaterialRow.node_id)
            .limit(1)
        )
        row = await session.scalar(statement)
    if row is None:
        return None
    entity = await session.get(EntityRow, row.node_id)
    return (await MaterialBook.load(session)).props(entity.world_id if entity is not None else None, row.material, row.world_material_id)
