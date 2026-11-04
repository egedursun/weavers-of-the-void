from types import MappingProxyType

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MINERAL_KINDS, MaterialKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

C = CommodityKind
M = MaterialKind
RENEWABLE = frozenset({C.TIMBER, C.FISH, C.LIVESTOCK, C.GRAIN, C.FODDER, C.MOUNTS, C.MAGICAL_REAGENTS, C.INCENSE})
LEGACY_YIELD: MappingProxyType[Commodity, CommodityKind] = MappingProxyType({Commodity.FOOD: C.GRAIN, Commodity.ORE: C.ORE, Commodity.GOODS: C.TIMBER})
BYPRODUCTS: MappingProxyType[MaterialKind, tuple[MaterialKind, int]] = MappingProxyType({M.LEAD: (M.SILVER, 10), M.COPPER: (M.GOLD, 3), M.IRON: (M.SULFUR, 5)})
REQUIRED: MappingProxyType[CommodityKind, tuple[KnowledgeBranch, int]] = MappingProxyType(
    {C.FISH: (KnowledgeBranch.SEAFARING, 0), C.MOUNTS: (KnowledgeBranch.AGRICULTURE, 1), C.MAGICAL_REAGENTS: (KnowledgeBranch.MAGIC, 1)}
)
DIFFICULTY: MappingProxyType[CommodityKind, int] = MappingProxyType({C.ORE: 55, C.STONE: 40, C.TIMBER: 30, C.FISH: 25, C.MAGICAL_REAGENTS: 45})
STONE_KINDS = frozenset({M.STONE, M.CLAY, M.FLINT, M.OBSIDIAN})
MATERIAL_KEYS = frozenset(kind.value for kind in MaterialKind)


def seam_material(region: RegionEnvironmentRow | None) -> MaterialKind:
    if region is None or not region.mineral_layers:
        return M.IRON
    ranked = sorted(region.mineral_layers.items(), key=lambda item: (-item[1], item[0]))
    ranked = [(name, depth) for name, depth in ranked if name in MATERIAL_KEYS] or [(M.IRON.value, 0)]
    for name, _ in ranked:
        kind = MaterialKind(name)
        if kind in MINERAL_KINDS and kind not in STONE_KINDS:
            return kind
    return MaterialKind(ranked[0][0])


def default_material(commodity: CommodityKind, region: RegionEnvironmentRow | None) -> MaterialKind | None:
    if commodity is C.ORE:
        return seam_material(region)
    if commodity is C.STONE:
        return M.STONE
    if commodity is C.TIMBER:
        return M.WOOD
    return None


def profile_for(
    rules: Rules, resource: EntityRow, commodity: CommodityKind, material: MaterialKind | None, region: RegionEnvironmentRow | None
) -> ResourceProfileRow:
    table = rules.extraction
    abundance = stat(resource, "abundance")
    initial = PERCENT * table.reserve_per_abundance
    reserve = round_half_up((abundance if abundance is not None else PERCENT // 2) * table.reserve_per_abundance)
    value = stat(resource, "value")
    might = stat(resource, "might")
    roughness = region.roughness if region is not None else 0
    branch: KnowledgeBranch | None = None
    level = 0
    if material is not None and MATERIALS[material].branch is not None:
        branch, level = MATERIALS[material].branch, MATERIALS[material].level
    elif commodity in REQUIRED:
        branch, level = REQUIRED[commodity]
    byproduct = BYPRODUCTS.get(material) if material is not None else None
    return ResourceProfileRow(
        resource_entity_id=resource.id,
        commodity=commodity,
        material=material,
        reserve=reserve,
        initial_reserve=initial,
        richness=clamp_int(value if value is not None else PERCENT // 2, 1, PERCENT),
        regeneration=round_half_up(initial * table.renewable_regen_pct / PERCENT) if commodity in RENEWABLE else 0,
        extraction_difficulty=clamp_int(DIFFICULTY.get(commodity, 20) + roughness // 4, 0, PERCENT),
        required_branch=branch,
        required_level=level,
        quality=clamp_int(might if might is not None else PERCENT // 2, 0, PERCENT),
        byproduct_material=byproduct[0] if byproduct is not None else None,
        byproduct_pct=byproduct[1] if byproduct is not None else 0,
        revealed=True,
    )


async def ensure_profile(
    session: AsyncSession,
    rules: Rules,
    resource: EntityRow,
    region: RegionEnvironmentRow | None,
    *,
    commodity: CommodityKind | None = None,
    material: MaterialKind | None = None,
) -> ResourceProfileRow:
    row = await session.get(ResourceProfileRow, resource.id)
    if row is not None:
        return row
    kind = commodity or C.ORE
    row = profile_for(rules, resource, kind, material if material is not None else default_material(kind, region), region)
    session.add(row)
    await session.flush()
    return row


async def set_resource_yield(
    session: AsyncSession, rules: Rules, resource_id: int, commodity: CommodityKind, material: MaterialKind | None = None
) -> ResourceProfileRow:
    resource = await session.get(EntityRow, resource_id)
    if resource is None or resource.entity_type is not EntityType.RESOURCE:
        raise NotFoundError("No such resource.")
    if material is not None and commodity in (C.ORE, C.STONE, C.TIMBER) and material not in MATERIALS:
        raise ValidationFailedError("That material is unknown.")
    row = await session.get(ResourceProfileRow, resource_id)
    if row is None:
        row = profile_for(rules, resource, commodity, material if material is not None else default_material(commodity, None), None)
        session.add(row)
    else:
        row.commodity = commodity
        row.material = material if material is not None else default_material(commodity, None)
        row.regeneration = round_half_up(row.initial_reserve * rules.extraction.renewable_regen_pct / PERCENT) if commodity in RENEWABLE else 0
    set_stats(resource, abundance=clamp_int(round_half_up(row.reserve * PERCENT / max(1, row.initial_reserve)), 0, PERCENT))
    await session.flush()
    return row
