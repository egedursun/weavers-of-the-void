from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.materials import ALLOYS, MATERIALS, MaterialSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import PROPERTY_COLUMNS, NodeMaterialRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import FoeNature, MaterialFamily, MaterialOrigin, MaterialSlot
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class MaterialProps:
    label: str
    family: MaterialFamily
    hardness: int
    toughness: int
    weight: int
    edge: int
    conductivity: int
    sanctity: int
    corruption: int
    rarity: int
    base_value: int
    decay: int
    branch: KnowledgeBranch | None
    level: int
    gate: KnowledgeBranch | None = None
    kind: MaterialKind | None = None
    world_material_id: int | None = None


def from_spec(item: MaterialSpec) -> MaterialProps:
    return MaterialProps(
        item.label,
        item.family,
        item.hardness,
        item.toughness,
        item.weight,
        item.edge,
        item.conductivity,
        item.sanctity,
        item.corruption,
        item.rarity,
        item.base_value,
        item.decay,
        item.branch,
        item.level,
        item.gate,
        item.kind,
    )


def from_row(row: WorldMaterialRow, gate: KnowledgeBranch | None = None, fallback: str | None = None) -> MaterialProps:
    label = row.name or fallback or (MATERIALS[row.base_kind].label if row.base_kind is not None else "an unnamed substance")
    values = {column: getattr(row, column) for column in PROPERTY_COLUMNS}
    return MaterialProps(label=label, family=row.family, branch=row.branch, level=row.level, gate=gate, kind=row.base_kind, world_material_id=row.id, **values)


@dataclass
class MaterialBook:
    overrides: dict[tuple[int, MaterialKind], WorldMaterialRow] = field(default_factory=dict)
    procedural: dict[int, WorldMaterialRow] = field(default_factory=dict)

    names: dict[int, str] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "MaterialBook":
        book = cls()
        for row in await session.scalars(select(WorldMaterialRow).order_by(WorldMaterialRow.id)):
            if row.origin is MaterialOrigin.CATALOG and row.base_kind is not None:
                book.overrides[(row.world_id, row.base_kind)] = row
            else:
                book.procedural[row.id] = row
        deposits = {row.deposit_entity_id: row.id for row in book.procedural.values() if row.deposit_entity_id is not None}
        if deposits:
            for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(deposits)))):
                book.names[deposits[entity_id]] = name
        return book

    def props(self, world_id: int | None, material: MaterialKind | None = None, world_material_id: int | None = None) -> MaterialProps | None:
        if world_material_id is not None and world_material_id in self.procedural:
            row = self.procedural[world_material_id]
            return from_row(row, fallback=self.names.get(row.id))
        if material is None:
            return None
        override = self.overrides.get((world_id, material)) if world_id is not None else None
        if override is not None:
            return from_row(override, MATERIALS[material].gate)
        return from_spec(MATERIALS[material])

    def of_world(self, world_id: int) -> list[WorldMaterialRow]:
        return [row for row in self.procedural.values() if row.world_id == world_id]


def workable(rules: Rules, props: MaterialProps, levels: Mapping[KnowledgeBranch, int], magic_density: int = 0) -> bool:
    if props.branch is not None and levels.get(props.branch, 0) < max(1, props.level):
        return False
    if props.gate is KnowledgeBranch.MAGIC:
        return magic_density >= rules.materials.skysteel_magic_density and levels.get(KnowledgeBranch.MAGIC, 0) >= 1
    if props.gate is not None:
        return levels.get(props.gate, 0) >= 1 or levels.get(KnowledgeBranch.FORBIDDEN, 0) >= 1
    return True


def alloy_inputs(material: MaterialKind) -> tuple[MaterialKind, ...]:
    return ALLOYS.get(material, (material,))


def weapon_damage(rules: Rules, props: MaterialProps, quality: int) -> int:
    table = rules.materials
    raw = props.hardness * table.damage_hardness_pct + props.edge * table.damage_edge_pct + quality * table.damage_quality_pct
    return clamp_int(round_half_up(raw / PERCENT), 0, PERCENT)


def armour_protection(rules: Rules, props: MaterialProps, quality: int) -> int:
    table = rules.materials
    raw = props.hardness * table.protection_hardness_pct + props.toughness * table.protection_toughness_pct + quality * table.protection_quality_pct
    return clamp_int(round_half_up(raw / PERCENT), 0, PERCENT)


def enchantment_cap(rules: Rules, props: MaterialProps) -> int:
    return clamp_int(rules.materials.enchant_floor + round_half_up(props.conductivity * rules.materials.enchant_conductivity_pct / PERCENT), 0, PERCENT)


def curse_bonus(rules: Rules, props: MaterialProps) -> int:
    return round_half_up(props.corruption * rules.materials.curse_corruption_pct / PERCENT)


def decay_loss(rules: Rules, props: MaterialProps, temperature: int) -> int:
    table = rules.materials
    warm = table.warm_decay_pct if temperature >= table.warm_temperature else PERCENT
    return round_half_up(props.decay * table.decay_per_epoch_pct / PERCENT * warm / PERCENT)


def march_drag(rules: Rules, props: MaterialProps) -> int:
    return round_half_up(props.weight * rules.materials.march_weight_pct / PERCENT)


def heat_attrition(rules: Rules, props: MaterialProps, temperature: int) -> int:
    table = rules.materials
    if temperature < table.warm_temperature:
        return 0
    return round_half_up(props.weight * table.heat_weight_pct / PERCENT)


def sanctity_splendour(rules: Rules, props: MaterialProps) -> int:
    return round_half_up(props.sanctity * rules.materials.sanctity_splendour_pct / PERCENT)


def sanctity_ward(rules: Rules, props: MaterialProps) -> int:
    return round_half_up(props.sanctity * rules.materials.sanctity_ward_pct / PERCENT)


def corruption_lure(rules: Rules, props: MaterialProps) -> int:
    return round_half_up(props.corruption * rules.materials.corruption_lure_pct / PERCENT)


MIDDLE = PERCENT // 2
WORTH_FLOOR = 0.1


def worth(props: MaterialProps) -> float:
    return (props.rarity + props.base_value) / 2


def worth_factor(rules: Rules, props: MaterialProps | None) -> float:
    if props is None:
        return 1.0
    return max(WORTH_FLOOR, 1 + (worth(props) - MIDDLE) / PERCENT * rules.materials.item_worth_pct / PERCENT)


def price_premium(rules: Rules, props: MaterialProps | None) -> float:
    if props is None:
        return 1.0
    table = rules.markets
    lift = ((props.rarity - MIDDLE) * table.rarity_price_pct + (props.base_value - MIDDLE) * table.value_price_pct) / PERCENT / PERCENT
    return max(WORTH_FLOOR, 1 + lift)


def battle_wear(rules: Rules, props: MaterialProps | None) -> int:
    base = rules.item_wear.battle_wear
    if props is None:
        return base
    return round_half_up(base * (1 - props.toughness / PERCENT * rules.materials.battle_toughness_pct / PERCENT))


def rust_wear(rules: Rules, props: MaterialProps) -> int:
    table = rules.materials
    return round_half_up(rules.item_wear.decay_wet * props.decay / table.rust_decay_step * table.rust_decay_pct / PERCENT)


def hull_guard(rules: Rules, props: MaterialProps | None) -> float:
    if props is None:
        return 1.0
    return max(0.0, 1 - (props.hardness + props.toughness) / 2 / PERCENT * rules.materials.hull_guard_pct / PERCENT)


def hull_wear(rules: Rules, props: MaterialProps | None, loss: int) -> int:
    if props is None:
        return loss
    return round_half_up(loss * (1 - props.toughness / PERCENT * rules.materials.hull_wear_pct / PERCENT))


def light_fabric(rules: Rules, props: MaterialProps | None) -> bool:
    return props is not None and props.weight <= rules.materials.fabric_light_weight


def wind_guard(rules: Rules, props: MaterialProps | None) -> float:
    if props is None:
        return 1.0
    return max(0.0, 1 - props.toughness / PERCENT * rules.materials.fabric_wind_pct / PERCENT)


def holy_edge(rules: Rules, props: MaterialProps | None, natures: frozenset[FoeNature]) -> float:
    if props is None or not natures:
        return 1.0
    table = rules.materials
    lift = 0.0
    for nature in natures:
        if nature is FoeNature.UNDEAD:
            lift += props.sanctity * table.sanctity_undead_pct / PERCENT / PERCENT
        elif nature is FoeNature.CURSED:
            lift += props.sanctity * table.sanctity_cursed_pct / PERCENT / PERCENT
        elif nature is FoeNature.VOID:
            lift += (props.sanctity * table.sanctity_void_pct - props.corruption * table.corruption_void_pct) / PERCENT / PERCENT
    return max(WORTH_FLOOR, 1 + lift)


async def node_material(session: AsyncSession, node_id: int, slot: MaterialSlot = MaterialSlot.BODY) -> NodeMaterialRow | None:
    return await session.get(NodeMaterialRow, (node_id, slot))


async def set_node_material(
    session: AsyncSession,
    node_id: int,
    slot: MaterialSlot,
    material: MaterialKind | None,
    world_material_id: int | None = None,
    *,
    force: bool = False,
) -> None:
    row = await session.get(NodeMaterialRow, (node_id, slot))
    if row is not None and row.held and not force:
        return
    if material is None and world_material_id is None:
        if row is not None:
            await session.delete(row)
        return
    if row is None:
        session.add(NodeMaterialRow(node_id=node_id, slot=slot, material=material if world_material_id is None else None, world_material_id=world_material_id))
    else:
        row.material = material if world_material_id is None else None
        row.world_material_id = world_material_id
    await session.flush()


@dataclass(frozen=True)
class VesselRig:
    hull: MaterialProps | None
    fabric: MaterialProps | None


async def slot_props(session: AsyncSession, node: EntityRow, slot: MaterialSlot, book: MaterialBook | None = None) -> MaterialProps | None:
    row = await session.get(NodeMaterialRow, (node.id, slot))
    if row is None:
        return None
    materials = book if book is not None else await MaterialBook.load(session)
    return materials.props(node.world_id, row.material, row.world_material_id)


async def rig_of(session: AsyncSession, vehicle: EntityRow | None) -> VesselRig | None:
    if vehicle is None:
        return None
    book = await MaterialBook.load(session)
    return VesselRig(await slot_props(session, vehicle, MaterialSlot.HULL, book), await slot_props(session, vehicle, MaterialSlot.FABRIC, book))
