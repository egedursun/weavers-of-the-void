from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.demography import GROWN_BANDS
from aerona.catalog.life.domain import STANDING_STATES
from aerona.catalog.life.structures import BUILDER_CONDITION, LIVING_ADULTS
from aerona.catalog.materials import MATERIALS
from aerona.catalog.peoples import STYLE_AXES, Style
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.demography import CohortRow, PeopleCultureRow
from aerona.db.tables.economy import NodeMaterialRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin, MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.geology import BuildingGrade
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.structure import BuilderKind, ConstructionState, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.economy.materials import MaterialProps, from_row, from_spec, set_node_material
from aerona.engine.environment.columns import columns_by_region, quarry_grade
from aerona.engine.lore.style import axis_of, style_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.structures.integrity import integrity_share
from aerona.engine.structures.spec import Resolved, capacity_of, resolve, staff_needed, upkeep_of
from aerona.rules.registry import Rules

HOST_HOPS = 4
BUILDER_KINDS = {
    EntityType.POLITY: BuilderKind.POLITY,
    EntityType.FACTION: BuilderKind.FACTION,
    EntityType.CULT: BuilderKind.CULT,
    EntityType.MORTAL: BuilderKind.PATRON,
    EntityType.SETTLEMENT: BuilderKind.COMMUNITY,
    EntityType.PEOPLE: BuilderKind.COMMUNITY,
}


MADE_ORIGINS = frozenset({MindOrigin.MADE, MindOrigin.GROWN, MindOrigin.TRAINED, MindOrigin.COPIED})


async def stone_condition(session: AsyncSession, rules: Rules, structure: EntityRow) -> int:
    region_id = (await RegionAtlas.load(session)).top_region(structure.id)
    if region_id is None:
        return 0
    grade = quarry_grade((await columns_by_region(session, [region_id])).get(region_id, []))
    return {BuildingGrade.PLAIN: 0, BuildingGrade.FINE: rules.rocks.fine_condition, BuildingGrade.SPLENDID: rules.rocks.splendid_condition}[grade]


async def builder_kind_found(session: AsyncSession, builder: EntityRow | SonRow | None) -> BuilderKind | None:
    if isinstance(builder, EntityRow):
        if await session.get(CompanyProfileRow, builder.id) is not None:
            return BuilderKind.COMPANY
        mind = await session.get(MindProfileRow, builder.id)
        if mind is not None and mind.origin in MADE_ORIGINS:
            return BuilderKind.MADE_MIND
    return builder_kind_of(builder)


def builder_kind_of(builder: EntityRow | SonRow | None) -> BuilderKind | None:
    if builder is None:
        return None
    if isinstance(builder, SonRow):
        return BuilderKind.GOD
    return BUILDER_KINDS.get(builder.entity_type, BuilderKind.COMMUNITY)


async def design_of(session: AsyncSession, profile: StructureProfileRow) -> StructureDesignRow | None:
    return await session.get(StructureDesignRow, profile.design_id) if profile.design_id is not None else None


async def resolved_of(session: AsyncSession, profile: StructureProfileRow) -> Resolved:
    return resolve(profile.kind, await design_of(session, profile))


async def material_props(session: AsyncSession, structure: EntityRow) -> MaterialProps | None:
    row = await session.get(NodeMaterialRow, (structure.id, MaterialSlot.BODY))
    if row is None:
        return None
    if row.world_material_id is not None:
        world = await session.get(WorldMaterialRow, row.world_material_id)
        return from_row(world) if world is not None else None
    if row.material is None:
        return None
    override = await session.scalar(
        select(WorldMaterialRow)
        .where(WorldMaterialRow.world_id == structure.world_id, WorldMaterialRow.base_kind == row.material, WorldMaterialRow.origin == MaterialOrigin.CATALOG)
        .limit(1)
    )
    return from_row(override, MATERIALS[row.material].gate) if override is not None else from_spec(MATERIALS[row.material])


def durability_from(rules: Rules, props: MaterialProps | None) -> int:
    table = rules.construction
    if props is None:
        return rules.deep_life.structure_durability_base
    raw = (
        rules.deep_life.structure_durability_base
        + props.hardness * table.durability_hardness_pct / PERCENT
        + props.toughness * table.durability_toughness_pct / PERCENT
        - props.decay * table.durability_decay_pct / PERCENT
    )
    return clamp_int(raw, 1, PERCENT)


def fire_resistance_from(rules: Rules, props: MaterialProps | None) -> int:
    table = rules.construction
    if props is None:
        return table.fire_organic
    return {
        MaterialFamily.ORGANIC: table.fire_organic,
        MaterialFamily.STONE: table.fire_stone,
        MaterialFamily.METAL: table.fire_metal,
        MaterialFamily.PRECIOUS: table.fire_precious,
        MaterialFamily.EXOTIC: table.fire_exotic,
    }[props.family]


async def host_for(session: AsyncSession, structure: EntityRow) -> EntityRow | None:
    current = await session.get(EntityRow, structure.location_id) if structure.location_id is not None else None
    for _ in range(HOST_HOPS):
        if current is None:
            break
        if current.entity_type in COMMUNITY_TYPES:
            return current
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    maker = await session.get(EntityRow, structure.maker_entity_id) if structure.maker_entity_id is not None else None
    return maker if maker is not None and maker.entity_type in COMMUNITY_TYPES and maker.status is EntityStatus.CANON else None


async def style_for(session: AsyncSession, community: EntityRow | None) -> Style | None:
    if community is None:
        return None
    people = community if community.entity_type is EntityType.PEOPLE else await people_of(session, community)
    return style_of(await session.get(PeopleCultureRow, people.id) if people is not None else None)


def style_column(axis: str) -> str:
    return f"style_{axis}"


def style_snapshot(style: Style | None) -> dict[str, int | None]:
    return {style_column(axis): (axis_of(style, axis) if style is not None else None) for axis in STYLE_AXES}


def kept_style(profile: StructureProfileRow) -> Style | None:
    values = [getattr(profile, style_column(axis)) for axis in STYLE_AXES]
    if any(value is None for value in values):
        return None
    return Style(*(int(value) for value in values))


async def adults_of(session: AsyncSession, community_id: int, social_class: str) -> int:
    summed = await session.scalar(
        select(func.coalesce(func.sum(CohortRow.count), 0)).where(
            CohortRow.community_entity_id == community_id,
            CohortRow.social_class == social_class,
            CohortRow.age_band.in_(sorted(GROWN_BANDS)),
            CohortRow.condition.in_(LIVING_ADULTS),
        )
    )
    return int(summed or 0)


async def staff_taken(session: AsyncSession, community_id: int, social_class: str, structure_id: int) -> int:
    summed = await session.scalar(
        select(func.coalesce(func.sum(StructureStaffRow.allocated), 0)).where(
            StructureStaffRow.community_entity_id == community_id,
            StructureStaffRow.social_class == social_class,
            StructureStaffRow.structure_entity_id != structure_id,
        )
    )
    return int(summed or 0)


@memoized(StructureStaffRow)
async def staff_of(session: AsyncSession, structure_id: int) -> tuple[StructureStaffRow, ...]:
    return tuple(await session.scalars(select(StructureStaffRow).where(StructureStaffRow.structure_entity_id == structure_id)))


async def staff_rows(session: AsyncSession, structure_id: int) -> list[StructureStaffRow]:
    return list(await staff_of(session, structure_id))


async def allocate_staff(session: AsyncSession, rules: Rules, profile: StructureProfileRow, resolved: Resolved) -> int:
    rows = await staff_rows(session, profile.structure_entity_id)
    needed = staff_needed(rules, resolved, profile.level)
    if resolved.staff_class is None or needed <= 0:
        for row in rows:
            await session.delete(row)
        return PERCENT
    found = next((item for item in rows if item.social_class is resolved.staff_class), None)
    for stale in [item for item in rows if item is not found]:
        await session.delete(stale)
    staff = found
    if staff is None:
        staff = StructureStaffRow(
            structure_entity_id=profile.structure_entity_id,
            social_class=resolved.staff_class,
            community_entity_id=profile.host_entity_id,
            required=0,
            allocated=0,
        )
        session.add(staff)
    staff.required = needed
    staff.community_entity_id = profile.host_entity_id
    if not staff.held:
        if profile.host_entity_id is None or profile.construction_state not in STANDING_STATES:
            staff.allocated = 0
        else:
            pool = round_half_up(await adults_of(session, profile.host_entity_id, resolved.staff_class.value) * rules.upkeep.staff_share_pct / PERCENT)
            free = max(0, pool - await staff_taken(session, profile.host_entity_id, resolved.staff_class.value, profile.structure_entity_id))
            staff.allocated = min(needed, free)
    await session.flush()
    return clamp_int(staff.allocated * PERCENT / needed, 0, PERCENT)


def condition_factor(rules: Rules, condition: int) -> float:
    return 1.0 if condition >= rules.structure_functions.condition_threshold else condition / PERCENT


def effect_of(rules: Rules, structure: EntityRow, profile: StructureProfileRow, resolved: Resolved) -> int:
    if profile.construction_state not in STANDING_STATES:
        return 0
    base = stat_or(structure, "function", rules.deep_life.structure_function_base) * resolved.function_pct / PERCENT
    ley = 1 + rules.structure_functions.ley_bonus_pct / PERCENT if profile.on_ley_line and resolved.ley else 1.0
    dated = 1 - rules.discovery.obsolete_pct / PERCENT if profile.obsolete_since is not None else 1.0
    return clamp_int(base * profile.staff_pct / PERCENT * condition_factor(rules, profile.condition) * ley * dated, 0, PERCENT)


def standing_state(rules: Rules, profile: StructureProfileRow) -> ConstructionState:
    if profile.condition <= 0:
        return ConstructionState.RUINED
    return ConstructionState.DAMAGED if profile.condition < rules.upkeep.damaged_below else ConstructionState.COMPLETE


async def refresh(session: AsyncSession, rules: Rules, structure: EntityRow, profile: StructureProfileRow) -> Resolved:
    resolved = await resolved_of(session, profile)
    if "capacity" not in profile.locked:
        profile.capacity = capacity_of(rules, resolved, profile.level)
    coin, goods = upkeep_of(rules, resolved, profile.level)
    if "upkeep_coin" not in profile.locked:
        profile.upkeep_coin = coin
    if "upkeep_goods" not in profile.locked:
        profile.upkeep_goods = goods
    if "staff_pct" not in profile.locked:
        profile.staff_pct = await allocate_staff(session, rules, profile, resolved)
    if "effect_pct" not in profile.locked:
        profile.effect_pct = round_half_up(effect_of(rules, structure, profile, resolved) * await integrity_share(session, structure.id))
    return resolved


async def ensure_profile(
    session: AsyncSession,
    rules: Rules,
    epoch: int,
    structure: EntityRow,
    kind: StructureKind,
    *,
    state: ConstructionState = ConstructionState.COMPLETE,
    level: int = 1,
    design_id: int | None = None,
    builder: EntityRow | SonRow | None = None,
    architect_id: int | None = None,
    son_id: int | None = None,
    material: MaterialKind | None = None,
    world_material_id: int | None = None,
) -> StructureProfileRow:
    profile = await session.get(StructureProfileRow, structure.id)
    if profile is not None:
        return profile
    if material is not None or world_material_id is not None:
        await set_node_material(session, structure.id, MaterialSlot.BODY, material, world_material_id)
    props = await material_props(session, structure)
    host = await host_for(session, structure)
    community = builder if isinstance(builder, EntityRow) and builder.entity_type in COMMUNITY_TYPES else host
    standing = state in STANDING_STATES
    if stat(structure, "durability") is None or (standing and material is not None):
        set_stats(structure, durability=durability_from(rules, props))
    built_by = await builder_kind_found(session, builder)
    stone = await stone_condition(session, rules, structure)
    profile = StructureProfileRow(
        structure_entity_id=structure.id,
        kind=kind,
        design_id=design_id,
        level=level,
        capacity=0,
        condition=clamp_int(stat_or(structure, "durability", PERCENT) + (BUILDER_CONDITION[built_by] if built_by is not None else 0) + stone, 0, PERCENT),
        construction_state=state,
        progress=PERCENT if standing else 0,
        fire_resistance=fire_resistance_from(rules, props),
        host_entity_id=host.id if host is not None else None,
        builder_entity_id=builder.id if builder is not None else None,
        builder_kind=built_by,
        architect_entity_id=architect_id,
        dedicated_son_id=son_id,
        **style_snapshot(await style_for(session, community)),
        on_ley_line=False,
        anchor=False,
        effect_pct=0,
        staff_pct=0,
        upkeep_coin=0,
        upkeep_goods=0,
        unpaid_epochs=0,
        built_epoch=epoch if standing else None,
        updated_epoch=epoch,
        locked=[],
    )
    session.add(profile)
    await session.flush()
    await refresh(session, rules, structure, profile)
    return profile


async def profiles_at(session: AsyncSession, host_id: int) -> list[StructureProfileRow]:
    return list(
        await session.scalars(
            select(StructureProfileRow).where(StructureProfileRow.host_entity_id == host_id).order_by(StructureProfileRow.structure_entity_id)
        )
    )


def lock(locked: list[str], key: str) -> list[str]:
    return locked if key in locked else [*locked, key]
