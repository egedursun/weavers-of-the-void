from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.structures import MEGASTRUCTURES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.integrity import (
    DESIGN_SECTION_FIELDS,
    MEGASTRUCTURE_FIELDS,
    STRUCTURE_SECTION_FIELDS,
    MegastructureRow,
    StructureDesignSectionRow,
    StructureSectionRow,
)
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import ConstructionRow, StructureDesignRow, StructureProfileRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.integrity import Criticality, HarmForce
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import (
    STRUCTURE_LEVEL_MAX,
    BuilderKind,
    BuildingForm,
    BuildScale,
    ConstructionState,
    ConstructionStatus,
    SectionRole,
    StaffScale,
    StructureKind,
    StructureSection,
)
from aerona.engine.collective.embodied import embody, settle
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.economy.materials import set_node_material
from aerona.engine.gatherings.control import Values, allowed
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.structures.construction import Commission, abandon, begin, construction_of, finish
from aerona.engine.structures.damage import consequences, harm
from aerona.engine.structures.integrity import StructureStrike, ensure_sections, match_condition, overall, sections_of, state_for, wound
from aerona.engine.structures.megastructures import state_of
from aerona.engine.structures.profiles import fire_resistance_from, lock, material_props, refresh, staff_rows
from aerona.engine.structures.spec import resolve, slots_for, tier_allows

PROFILE_NUMBERS: dict[str, tuple[int, int]] = {
    "level": (1, STRUCTURE_LEVEL_MAX),
    "capacity": (0, 10**9),
    "condition": (0, PERCENT),
    "progress": (0, PERCENT),
    "fire_resistance": (0, PERCENT),
    "effect_pct": (0, PERCENT),
    "staff_pct": (0, PERCENT),
    "upkeep_coin": (0, 10**9),
    "upkeep_goods": (0, 10**9),
    "unpaid_epochs": (0, 10**6),
    "style_ornament": (0, PERCENT),
    "style_geometry": (0, PERCENT),
    "style_colour": (0, PERCENT),
    "style_scale": (0, PERCENT),
    "style_symmetry": (0, PERCENT),
}
PROFILE_FLAGS = ("on_ley_line", "anchor")
PROFILE_REFS = ("host_entity_id", "architect_entity_id", "builder_entity_id", "dedicated_son_id", "design_id")
STAT_NUMBERS = ("splendor", "durability", "function")
CONSTRUCTION_NUMBERS: dict[str, tuple[int, int]] = {"cost": (1, 10**9), "work": (0, 10**9), "funds": (0, 10**12)}
DESIGN_NUMBERS: dict[str, tuple[int, int]] = {
    "capacity_pct": (0, 1000),
    "cost_pct": (1, 1000),
    "upkeep_pct": (0, 1000),
    "function_pct": (0, 300),
    "staff_pct": (0, 1000),
    "storeys": (1, 200),
}
DESIGN_CHOICES = {
    "staff_class": SocialClass,
    "staff_scale": StaffScale,
    "scale": BuildScale,
    "upkeep_commodity": CommodityKind,
    "min_tier": SizeTier,
    "base_kind": StructureKind,
    "form": BuildingForm,
    "material": MaterialKind,
}
Value = int | str | bool | None


def bounded(key: str, value: Value, low: int, high: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from {low} to {high}.")
    return value


async def structure(ctx: TickContext, structure_id: int) -> tuple[EntityRow, StructureProfileRow]:
    work = await ctx.session.get(EntityRow, structure_id)
    profile = await ctx.session.get(StructureProfileRow, structure_id)
    if work is None or work.entity_type is not EntityType.STRUCTURE or profile is None:
        raise NotFoundError("No such structure.")
    return work, profile


async def free_slots(ctx: TickContext, site: EntityRow) -> int:
    town = await ctx.session.get(SettlementProfileRow, site.id)
    rows = await ctx.session.scalars(
        select(StructureProfileRow.structure_entity_id).where(
            StructureProfileRow.host_entity_id == site.id, StructureProfileRow.construction_state != ConstructionState.RUINED
        )
    )
    total = slots_for(ctx.rules, town.size_tier) if town is not None else ctx.rules.construction.slots_base
    return total - len(list(rows))


async def commission(
    ctx: TickContext,
    site_id: int,
    kind: StructureKind,
    *,
    level: int = 1,
    design: StructureDesignRow | None = None,
    material: MaterialKind | None = None,
    world_material_id: int | None = None,
    name: str | None = None,
    son_id: int | None = None,
    builder_id: int | None = None,
    builder_son_id: int | None = None,
    architect_id: int | None = None,
    funds: int = 0,
    player: bool = False,
) -> tuple[EntityRow, ConstructionRow]:
    site = await ctx.session.get(EntityRow, site_id)
    if site is None or site.status is not EntityStatus.CANON or site.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only a living settlement or people can raise a structure.")
    bounded("level", level, 1, STRUCTURE_LEVEL_MAX)
    if design is not None and (design.retired or design.base_kind is not kind):
        raise ValidationFailedError(f"{design.name} is not a design for {an(kind.value.replace('_', ' '))}.")
    resolved = resolve(kind, design)
    town = await ctx.session.get(SettlementProfileRow, site.id)
    if town is not None and not tier_allows(town.size_tier, resolved):
        raise ValidationFailedError(f"{site.name} is too small for {resolved.label.lower()}: it needs to be {an(resolved.min_tier.value)} or larger.")
    if await free_slots(ctx, site) <= 0:
        raise ValidationFailedError(f"{site.name} has no room left for another structure; raze or let one fall first.")
    builder: EntityRow | SonRow | None = None
    if builder_son_id is not None:
        builder = await ctx.session.get(SonRow, builder_son_id)
    elif builder_id is not None:
        builder = await ctx.session.get(EntityRow, builder_id)
        if builder is None:
            raise ValidationFailedError("The builder does not exist.")
    order = Commission(
        site=site,
        kind=kind,
        level=level,
        design=design,
        builder=builder,
        architect_id=architect_id,
        son_id=son_id,
        material=material,
        world_material_id=world_material_id,
        name=name,
        player=player,
        funds=funds,
    )
    return await begin(ctx, order)


async def fund(ctx: TickContext, structure_id: int, amount: int) -> ConstructionRow:
    bounded("amount", amount, 1, 10**12)
    row = await construction_of(ctx, structure_id)
    row.funds += amount
    row.stalled_epochs = 0
    await ctx.session.flush()
    return row


async def finish_now(ctx: TickContext, structure_id: int) -> EntityRow:
    row = await construction_of(ctx, structure_id)
    work = await finish(ctx, row, by_hand=True)
    if work is None:
        raise NotFoundError("No such structure.")
    return work


async def abandon_now(ctx: TickContext, structure_id: int, reason: str) -> ConstructionRow:
    row = await construction_of(ctx, structure_id)
    await abandon(ctx, row, reason or "its builders were called away")
    return row


async def set_staff(ctx: TickContext, structure_id: int, allocated: int | None, *, hold: bool) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    resolved = await refresh(ctx.session, ctx.rules, work, profile)
    rows = await staff_rows(ctx.session, structure_id)
    if resolved.staff_class is None or not rows:
        raise ValidationFailedError(f"{work.name} needs no staff.")
    row = rows[0]
    if allocated is not None:
        row.allocated = bounded("staff", allocated, 0, 10**9)
    row.held = hold
    await refresh(ctx.session, ctx.rules, work, profile)
    await ctx.session.flush()
    return profile


async def damage(ctx: TickContext, structure_id: int, amount: int, cause: str) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    bounded("damage", amount, 1, PERCENT)
    await harm(ctx, work, profile, amount, cause=cause or "the Creator's hand", force=HarmForce.DIVINE, even=True)
    await ctx.session.flush()
    return profile


def set_choice(target: object, key: str, value: Value, kind: type) -> None:
    if value is None:
        setattr(target, key, None)
        return
    try:
        setattr(target, key, kind(str(value)))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error


async def set_reference(ctx: TickContext, profile: StructureProfileRow, key: str, value: Value) -> None:
    if value is None:
        setattr(profile, key, None)
        if key == "builder_entity_id":
            profile.builder_kind = None
        return
    target = bounded(key, value, 1, 2**62)
    if key == "dedicated_son_id":
        if await ctx.session.get(SonRow, target) is None:
            raise ValidationFailedError("No such god.")
    elif key == "design_id":
        design = await ctx.session.get(StructureDesignRow, target)
        if design is None or design.retired:
            raise ValidationFailedError("No such design.")
        profile.kind = design.base_kind
    elif key == "builder_entity_id":
        son = await ctx.session.get(SonRow, target)
        entity = await ctx.session.get(EntityRow, target)
        if son is None and entity is None:
            raise ValidationFailedError("No such builder.")
        profile.builder_kind = BuilderKind.GOD if son is not None else None
    elif await ctx.session.get(EntityRow, target) is None:
        raise ValidationFailedError("No such record.")
    setattr(profile, key, target)


async def set_material(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, value: Value, world_material_id: int | None) -> None:
    material = MaterialKind(str(value)) if value is not None and world_material_id is None else None
    await set_node_material(ctx.session, work.id, MaterialSlot.BODY, material, world_material_id)
    if "fire_resistance" not in profile.locked:
        profile.fire_resistance = fire_resistance_from(ctx.rules, await material_props(ctx.session, work))


PROFILE_CHOICES: dict[str, type] = {
    "kind": StructureKind,
    "construction_state": ConstructionState,
    "builder_kind": BuilderKind,
}


async def set_field(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, key: str, value: Value, *, world_material_id: int | None) -> None:
    if key in PROFILE_NUMBERS:
        setattr(profile, key, bounded(key, value, *PROFILE_NUMBERS[key]))
    elif key in PROFILE_FLAGS:
        setattr(profile, key, bool(value))
    elif key in PROFILE_REFS:
        await set_reference(ctx, profile, key, value)
    elif key in PROFILE_CHOICES:
        set_choice(profile, key, value, PROFILE_CHOICES[key])
    elif key == "material":
        await set_material(ctx, work, profile, value, world_material_id)
    elif key in STAT_NUMBERS:
        set_stats(work, **{key: bounded(key, value, 0, PERCENT)})
    else:
        raise ValidationFailedError(f"Unknown structure field: {key}.")


async def edit_structure(
    ctx: TickContext, structure_id: int, values: Mapping[str, Value], *, release: list[str], world_material_id: int | None = None
) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    construction = await ctx.session.scalar(
        select(ConstructionRow).where(ConstructionRow.structure_entity_id == structure_id).order_by(ConstructionRow.id.desc()).limit(1)
    )
    for key, value in values.items():
        if key in CONSTRUCTION_NUMBERS and construction is not None:
            column = "progress" if key == "work" else key
            setattr(construction, column, bounded(key, value, *CONSTRUCTION_NUMBERS[key]))
            construction.locked = lock(construction.locked, column)
            continue
        await set_field(ctx, work, profile, key, value, world_material_id=world_material_id)
        profile.locked = lock(profile.locked, key)
        if key == "condition":
            await ensure_sections(ctx.session, work, profile)
            await match_condition(ctx.session, ctx.rules, work.id, profile.condition)
    for key in release:
        profile.locked = [item for item in profile.locked if item != key]
        if construction is not None:
            construction.locked = [item for item in construction.locked if item not in {key, "progress" if key == "work" else key}]
        if key == "staff":
            for row in await staff_rows(ctx.session, structure_id):
                row.held = False
    if construction is not None and construction.status is ConstructionStatus.ACTIVE:
        profile.progress = clamp_int(construction.progress * PERCENT / max(1, construction.cost), 0, PERCENT)
    await refresh(ctx.session, ctx.rules, work, profile)
    await ctx.session.flush()
    return profile


async def repair(ctx: TickContext, structure_id: int) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    profile.condition = stat_or(work, "durability", PERCENT)
    await ensure_sections(ctx.session, work, profile)
    await match_condition(ctx.session, ctx.rules, work.id, profile.condition)
    if profile.construction_state is ConstructionState.DAMAGED:
        profile.construction_state = ConstructionState.COMPLETE
    await refresh(ctx.session, ctx.rules, work, profile)
    await note(ctx, f"{work.name} was made whole again.", key="structures.repaired", ids=[work.id], kind=ChronicleKind.CONSTRUCTION)
    await ctx.session.flush()
    return profile


async def design(ctx: TickContext, design_id: int) -> StructureDesignRow:
    row = await ctx.session.get(StructureDesignRow, design_id)
    if row is None:
        raise NotFoundError("No such structure design.")
    return row


def apply_design(row: StructureDesignRow, values: Mapping[str, Value], *, hold: bool) -> None:
    for key, value in values.items():
        if key in DESIGN_NUMBERS:
            setattr(row, key, bounded(key, value, *DESIGN_NUMBERS[key]))
        elif key in DESIGN_CHOICES:
            if key == "base_kind" and value is None:
                raise ValidationFailedError("A design needs a base kind.")
            set_choice(row, key, value, DESIGN_CHOICES[key])
        elif key == "ley":
            row.ley = None if value is None else bool(value)
        elif key == "name":
            text = str(value or "").strip()
            if not text:
                raise ValidationFailedError("A design needs a name.")
            row.name = text
        elif key == "description":
            row.description = str(value) if value else None
        elif key == "origin_node_id":
            row.origin_node_id = value if isinstance(value, int) and not isinstance(value, bool) else None
        else:
            raise ValidationFailedError(f"Unknown design field: {key}.")
        if hold:
            row.locked = lock(row.locked, key)


async def create_design(ctx: TickContext, values: Mapping[str, Value], *, world_id: int | None, son_id: int | None = None) -> StructureDesignRow:
    if "base_kind" not in values or "name" not in values:
        raise ValidationFailedError("A design needs a name and a base kind.")
    if world_id is not None and await ctx.session.get(WorldRow, world_id) is None:
        raise ValidationFailedError("No such world.")
    row = StructureDesignRow(
        world_id=world_id,
        name="",
        base_kind=StructureKind.MONUMENT,
        capacity_pct=PERCENT,
        cost_pct=PERCENT,
        upkeep_pct=PERCENT,
        function_pct=PERCENT,
        staff_pct=PERCENT,
        creator_son_id=son_id,
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
    )
    apply_design(row, values, hold=False)
    ctx.session.add(row)
    await ctx.session.flush()
    await embody(ctx.session, row)
    return row


async def edit_design(ctx: TickContext, design_id: int, values: Mapping[str, Value], *, release: list[str]) -> StructureDesignRow:
    row = await design(ctx, design_id)
    apply_design(row, values, hold=True)
    row.locked = [item for item in row.locked if item not in release]
    await refresh_designed(ctx, row.id)
    await ctx.session.flush()
    await settle(ctx.session, row)
    return row


async def retire_design(ctx: TickContext, design_id: int, retired: bool) -> StructureDesignRow:
    row = await design(ctx, design_id)
    row.retired = retired
    await refresh_designed(ctx, row.id)
    await ctx.session.flush()
    await settle(ctx.session, row)
    return row


async def refresh_designed(ctx: TickContext, design_id: int) -> None:
    for profile in await ctx.session.scalars(select(StructureProfileRow).where(StructureProfileRow.design_id == design_id)):
        work = await ctx.session.get(EntityRow, profile.structure_entity_id)
        if work is not None:
            await refresh(ctx.session, ctx.rules, work, profile)


async def strike_section(ctx: TickContext, structure_id: int, section: StructureSection, damage: int) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    rows = await ensure_sections(ctx.session, work, profile)
    row = next((item for item in rows if item.section is section), None)
    if row is None:
        raise NotFoundError("This structure has no such section.")
    strike = StructureStrike()
    wound(ctx.rules, row, damage, strike)
    profile.condition = clamp_int(overall(rows), 0, PERCENT)
    await consequences(ctx, work, profile, strike)
    await refresh(ctx.session, ctx.rules, work, profile)
    await ctx.session.flush()
    return profile


async def repair_section(ctx: TickContext, structure_id: int, section: StructureSection) -> StructureProfileRow:
    work, profile = await structure(ctx, structure_id)
    rows = await ensure_sections(ctx.session, work, profile)
    row = next((item for item in rows if item.section is section), None)
    if row is None:
        raise NotFoundError("This structure has no such section.")
    row.condition = PERCENT
    row.state = state_for(ctx.rules, row.condition)
    profile.condition = clamp_int(overall(rows), 0, PERCENT)
    await refresh(ctx.session, ctx.rules, work, profile)
    await ctx.session.flush()
    return profile


async def edit_section(ctx: TickContext, structure_id: int, section: StructureSection, values: Values, release: list[str]) -> StructureSectionRow:
    work, profile = await structure(ctx, structure_id)
    rows = await ensure_sections(ctx.session, work, profile)
    row = next((item for item in rows if item.section is section), None)
    if row is None:
        row = StructureSectionRow(structure_entity_id=work.id, section=section, role=SectionRole.SHELTER, condition=PERCENT, locked=[])
        ctx.session.add(row)
        rows.append(row)
    apply(row, allowed(values, STRUCTURE_SECTION_FIELDS, "section of a structure"), release)
    if "condition" in values and "state" not in values:
        row.state = state_for(ctx.rules, row.condition)
    profile.condition = clamp_int(overall(rows), 0, PERCENT)
    await refresh(ctx.session, ctx.rules, work, profile)
    await ctx.session.flush()
    return row


async def remove_section(ctx: TickContext, structure_id: int, section: StructureSection) -> None:
    work, profile = await structure(ctx, structure_id)
    row = await ctx.session.get(StructureSectionRow, (structure_id, section))
    if row is None:
        raise NotFoundError("This structure has no such section.")
    await ctx.session.delete(row)
    await ctx.session.flush()
    profile.condition = clamp_int(overall(await sections_of(ctx.session, structure_id)), 0, PERCENT)
    await refresh(ctx.session, ctx.rules, work, profile)


async def set_design_section(ctx: TickContext, design_id: int, section: StructureSection, values: Values) -> StructureDesignSectionRow:
    await design(ctx, design_id)
    row = await ctx.session.get(StructureDesignSectionRow, (design_id, section))
    if row is None:
        row = StructureDesignSectionRow(design_id=design_id, section=section, criticality=Criticality.MINOR, share=10)
        ctx.session.add(row)
    apply(row, allowed(values, DESIGN_SECTION_FIELDS, "section of a structure design"), [])
    await ctx.session.flush()
    return row


async def remove_design_section(ctx: TickContext, design_id: int, section: StructureSection) -> None:
    row = await ctx.session.get(StructureDesignSectionRow, (design_id, section))
    if row is None:
        raise NotFoundError("This design has no such section.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_megastructure(ctx: TickContext, structure_id: int, values: Values, release: list[str]) -> MegastructureRow:
    work, profile = await structure(ctx, structure_id)
    if profile.kind not in MEGASTRUCTURES:
        raise ValidationFailedError(f"{work.name} is no megastructure.")
    row = await state_of(ctx.session, structure_id, ctx.epoch)
    apply(row, allowed(values, MEGASTRUCTURE_FIELDS, "megastructure"), release)
    await ctx.session.flush()
    return row


async def clear_megastructure(ctx: TickContext, structure_id: int) -> None:
    row = await ctx.session.get(MegastructureRow, structure_id)
    if row is None:
        raise NotFoundError("This megastructure keeps no state yet.")
    await ctx.session.delete(row)
    await ctx.session.flush()
