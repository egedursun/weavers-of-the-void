from dataclasses import dataclass

from aerona.catalog.structures import STRUCTURES
from aerona.constants.units import PERCENT
from aerona.db.tables.structures import StructureDesignRow
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.settlement import TIER_ORDER, SizeTier
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import BuildScale, CapacityUnit, StaffScale, StructureGroup, StructureKind
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

SCALE_ORDER = (BuildScale.MINOR, BuildScale.MAJOR, BuildScale.GRAND, BuildScale.WONDER)


@dataclass(frozen=True)
class Resolved:
    kind: StructureKind
    group: StructureGroup
    label: str
    staff_class: SocialClass | None
    staff_scale: StaffScale
    capacity_unit: CapacityUnit
    scale: BuildScale
    upkeep_commodity: CommodityKind
    min_tier: SizeTier
    ley: bool
    workshop: WorkshopKind | None
    branch: KnowledgeBranch | None
    capacity_pct: int = PERCENT
    cost_pct: int = PERCENT
    upkeep_pct: int = PERCENT
    function_pct: int = PERCENT
    staff_pct: int = PERCENT
    design_name: str | None = None


def resolve(kind: StructureKind, design: StructureDesignRow | None = None) -> Resolved:
    base = STRUCTURES[design.base_kind if design is not None else kind]
    if design is None:
        return Resolved(
            base.kind,
            base.group,
            base.label,
            base.staff,
            base.staff_scale,
            base.capacity,
            base.scale,
            base.upkeep,
            base.min_tier,
            base.ley,
            base.workshop,
            base.branch,
        )
    return Resolved(
        kind=base.kind,
        group=base.group,
        label=design.name,
        staff_class=design.staff_class if design.staff_class is not None else base.staff,
        staff_scale=design.staff_scale or base.staff_scale,
        capacity_unit=base.capacity,
        scale=design.scale or base.scale,
        upkeep_commodity=design.upkeep_commodity or base.upkeep,
        min_tier=design.min_tier or base.min_tier,
        ley=design.ley if design.ley is not None else base.ley,
        workshop=base.workshop,
        branch=base.branch,
        capacity_pct=design.capacity_pct,
        cost_pct=design.cost_pct,
        upkeep_pct=design.upkeep_pct,
        function_pct=design.function_pct,
        staff_pct=design.staff_pct,
        design_name=design.name,
    )


def per_level(rules: Rules, unit: CapacityUnit) -> int:
    table = rules.structure_functions
    return {
        CapacityUnit.NONE: 0,
        CapacityUnit.TONS: table.tons_per_level,
        CapacityUnit.VOLUMES: table.volumes_per_level,
        CapacityUnit.GARRISON: table.garrison_per_level,
        CapacityUnit.BEDS: table.beds_per_level,
        CapacityUnit.BERTHS: table.berths_per_level,
        CapacityUnit.SEATS: table.seats_per_level,
        CapacityUnit.CELLS: table.cells_per_level,
        CapacityUnit.WORSHIPPERS: table.worshippers_per_level,
        CapacityUnit.PUPILS: table.pupils_per_level,
        CapacityUnit.STALLS: table.stalls_per_level,
        CapacityUnit.HANDS: table.hands_per_level,
        CapacityUnit.LOADS: table.loads_per_level,
        CapacityUnit.TRAVELLERS: table.travellers_per_level,
    }[unit]


def capacity_of(rules: Rules, resolved: Resolved, level: int) -> int:
    return round_half_up(per_level(rules, resolved.capacity_unit) * level * resolved.capacity_pct / PERCENT)


def staff_needed(rules: Rules, resolved: Resolved, level: int) -> int:
    if resolved.staff_class is None:
        return 0
    table = rules.upkeep
    each = {StaffScale.NONE: 0, StaffScale.FEW: table.staff_few, StaffScale.SOME: table.staff_some, StaffScale.MANY: table.staff_many}[resolved.staff_scale]
    return round_half_up(each * level * resolved.staff_pct / PERCENT)


def build_cost(rules: Rules, resolved: Resolved, level: int) -> int:
    table = rules.construction
    base = {
        BuildScale.MINOR: table.cost_minor,
        BuildScale.MAJOR: table.cost_major,
        BuildScale.GRAND: table.cost_grand,
        BuildScale.WONDER: table.cost_wonder,
    }[resolved.scale]
    extra = max(0, level - 1) * table.level_cost_pct / PERCENT
    return max(1, round_half_up(base * (1 + extra) * resolved.cost_pct / PERCENT))


def upkeep_of(rules: Rules, resolved: Resolved, level: int) -> tuple[int, int]:
    table = rules.upkeep
    coin = {BuildScale.MINOR: table.coin_minor, BuildScale.MAJOR: table.coin_major, BuildScale.GRAND: table.coin_grand, BuildScale.WONDER: table.coin_wonder}
    goods = {
        BuildScale.MINOR: table.goods_minor,
        BuildScale.MAJOR: table.goods_major,
        BuildScale.GRAND: table.goods_grand,
        BuildScale.WONDER: table.goods_wonder,
    }
    levels = 1 if resolved.scale is BuildScale.WONDER else level
    return (
        round_half_up(coin[resolved.scale] * levels * resolved.upkeep_pct / PERCENT),
        round_half_up(goods[resolved.scale] * levels * resolved.upkeep_pct / PERCENT),
    )


def slots_for(rules: Rules, tier: SizeTier) -> int:
    return rules.construction.slots_base + TIER_ORDER.index(tier) * rules.construction.slots_per_tier


def tier_allows(tier: SizeTier, resolved: Resolved) -> bool:
    return TIER_ORDER.index(tier) >= TIER_ORDER.index(resolved.min_tier)


def scale_index(scale: BuildScale) -> int:
    return SCALE_ORDER.index(scale)
