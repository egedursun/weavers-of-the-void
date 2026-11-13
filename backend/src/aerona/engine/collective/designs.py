from dataclasses import dataclass
from statistics import fmean
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.vehicles import FAMILY_TECHNIQUES, FRAMES, FUELS, LAYOUTS, MOUNTS, SIZE_SCALE, FrameSpec
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.collective import ComponentWearRow, DesignComponentRow, DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.economy import WorkshopRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.db.tables.vehicles import DesignMountRow, DesignSectionRow, DesignTechniqueRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import DesignComponentKind, DesignKind
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.vehicles import FireControl, MountArc, MountKind, VehicleFrame, VehicleSection
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.equipment.models import mount_model
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.vehicles.sections import strike_vessel
from aerona.rules.registry import Rules

C = DesignComponentKind
M = MountKind
X = VehicleSection
FULL_SIZE = 10
TOUGH = 50
HALF = PERCENT // 2
FAILURE_TEXT = total(
    DesignComponentKind,
    {
        C.HULL: "sprang a leak",
        C.PROPULSION: "lost its means of moving",
        C.HOLD: "lost part of its cargo",
        C.QUARTERS: "lost crew to sickness and cold",
        C.NAVIGATION: "lost its way",
        C.ARMOUR: "had its armour give way",
        C.WEAPON: "had its weapons fail",
        C.WARD: "had its wards falter",
        C.FRAME: "had its frame crack",
        C.COUNTERWEIGHT: "lost its counterweight",
        C.STEERING: "lost its steering",
        C.LIFT: "lost lift",
        C.POWER: "lost power",
        C.TROOPS: "had its troop deck give way",
        C.COMMAND: "lost its command post",
        C.LIFE_SUPPORT: "had its life support falter",
    },
)
MOUNT_SECTIONS: MappingProxyType[MountKind, VehicleSection] = total(
    MountKind,
    {
        M.BOW: X.BOW,
        M.STERN: X.STERN,
        M.BROADSIDE: X.GUN_DECK,
        M.DECK: X.DECK,
        M.TURRET: X.TURRET,
        M.SPINAL: X.HULL,
        M.HARDPOINT: X.HARDPOINT,
        M.WING: X.WINGS,
        M.CREW_STATION: X.PLATFORM,
        M.RIDER: X.SADDLE,
        M.RAM: X.RAM_HEAD,
        M.BAY: X.CARGO_BAY,
        M.WARD_NODE: X.WARD,
    },
)
MOUNT_FALLBACKS = (X.DECK, X.PLATFORM, X.TURRET, X.HULL, X.CHASSIS, X.FRAME, X.GONDOLA, X.MOUNT_BODY, X.CORE)
MOUNT_ARCS: MappingProxyType[MountKind, MountArc] = total(
    MountKind,
    {
        M.BOW: MountArc.FORWARD,
        M.STERN: MountArc.AFT,
        M.BROADSIDE: MountArc.SIDE,
        M.DECK: MountArc.ALL_ROUND,
        M.TURRET: MountArc.ALL_ROUND,
        M.SPINAL: MountArc.FORWARD,
        M.HARDPOINT: MountArc.FORWARD,
        M.WING: MountArc.FORWARD,
        M.CREW_STATION: MountArc.ALL_ROUND,
        M.RIDER: MountArc.ALL_ROUND,
        M.RAM: MountArc.FORWARD,
        M.BAY: MountArc.ALL_ROUND,
        M.WARD_NODE: MountArc.ALL_ROUND,
    },
)
FIRE_ORDER = (
    FireControl.MANUAL,
    FireControl.DRILLED,
    FireControl.SIGHTED,
    FireControl.DIRECTED,
    FireControl.COMPUTED,
    FireControl.AUTOMATIC,
    FireControl.GUIDED,
)
ARMAMENT_NORM = 6
REFIT_QUALITY = 10
HULL_DAMAGE = 20
CREW_LOSS_PCT = 10


@dataclass
class DesignTally:
    drawn: int = 0
    refits: int = 0
    worn: int = 0
    failures: int = 0
    mended: int = 0


def frame_sizes(frame: VehicleFrame) -> dict[DesignComponentKind, int]:
    spec = FRAMES[frame]
    found = {
        C.HULL: spec.endurance // 10,
        C.FRAME: spec.structure // 15,
        C.PROPULSION: spec.speed // 10,
        C.HOLD: spec.cargo // 20,
        C.QUARTERS: spec.crew // 10,
        C.WEAPON: spec.slots * 2,
        C.ARMOUR: spec.armour // 10,
        C.WARD: 1 + spec.strangeness // 25,
        C.NAVIGATION: spec.range // 10,
        C.STEERING: 2,
        C.LIFT: 4,
        C.POWER: 4,
        C.TROOPS: spec.troops // 10,
        C.COMMAND: 2,
        C.LIFE_SUPPORT: 3,
        C.COUNTERWEIGHT: 3,
    }
    present = {part.function for part in LAYOUTS[spec.family]}
    return {kind: clamp_int(size, 1, FULL_SIZE) for kind, size in found.items() if kind in present}


async def components_of(session: AsyncSession, design_id: int) -> dict[DesignComponentKind, DesignComponentRow]:
    rows = await session.scalars(select(DesignComponentRow).where(DesignComponentRow.design_id == design_id))
    return {row.component: row for row in rows}


async def sections_of(session: AsyncSession, design_id: int) -> list[DesignSectionRow]:
    return list(await session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id == design_id).order_by(DesignSectionRow.section)))


async def mounts_of(session: AsyncSession, design_id: int) -> list[DesignMountRow]:
    return list(await session.scalars(select(DesignMountRow).where(DesignMountRow.design_id == design_id).order_by(DesignMountRow.slot, DesignMountRow.id)))


async def toughness(session: AsyncSession, part: DesignComponentRow) -> tuple[float, float, float]:
    material = await session.get(WorldMaterialRow, part.material_id) if part.material_id is not None else None
    if material is None:
        return 1.0, 1.0, 1.0
    return material.toughness / TOUGH, material.weight / TOUGH, 1 + material.decay / PERCENT


def worth(part: DesignComponentRow | None, tough: float = 1.0) -> float:
    return part.size * part.quality / PERCENT * tough if part is not None else 0.0


async def sync_components(session: AsyncSession, design: DesignRow) -> dict[DesignComponentKind, DesignComponentRow]:
    sections = await sections_of(session, design.id)
    existing = await components_of(session, design.id)
    if not sections:
        return existing
    grouped: dict[DesignComponentKind, list[DesignSectionRow]] = {}
    for row in sections:
        grouped.setdefault(row.function, []).append(row)
    for kind, rows in grouped.items():
        component = existing.get(kind)
        if component is None:
            component = DesignComponentRow(design_id=design.id, component=kind, size=0, quality=HALF)
            session.add(component)
            existing[kind] = component
        component.size = clamp_int(max(row.size for row in rows), 0, FULL_SIZE)
        component.quality = clamp_int(round_half_up(fmean(row.quality for row in rows)), 0, PERCENT)
        component.material_id = next((row.material_id for row in rows if row.material_id is not None), component.material_id)
    for kind, component in list(existing.items()):
        if kind not in grouped:
            await session.delete(component)
            existing.pop(kind)
    return existing


async def mount_firepower(session: AsyncSession, mounts: list[DesignMountRow]) -> float:
    found = 0.0
    for mount in mounts:
        model = await session.get(EquipmentModelRow, mount.model_id) if mount.model_id is not None else None
        if model is not None and mount.count > 0:
            found += model.damage * max(1, model.rate) * mount.count * (1 + model.piercing / (2 * PERCENT))
    return found


def aim(control: FireControl) -> float:
    return 0.8 + FIRE_ORDER.index(control) * 0.07


def ratio(
    parts: dict[DesignComponentKind, DesignComponentRow],
    tough: dict[DesignComponentKind, float],
    defaults: dict[DesignComponentKind, int],
    kind: DesignComponentKind,
) -> float:
    if kind not in parts or kind not in defaults:
        return 1.0
    return worth(parts[kind], tough.get(kind, 1.0)) / max(0.1, defaults[kind] * 0.5)


async def derive(session: AsyncSession, rules: Rules, design: DesignRow) -> DesignRow:
    if design.frame is None:
        await session.flush()
        return design
    spec = FRAMES[design.frame]
    parts = await sync_components(session, design)
    tough: dict[DesignComponentKind, float] = {}
    mass = 0.0
    for kind, part in parts.items():
        strength, weight, _ = await toughness(session, part)
        tough[kind] = strength
        mass += part.size * weight
    defaults = frame_sizes(design.frame)
    budget = rules.designs.mass_budget * SIZE_SCALE[design.size_class]
    burden = min(0.9, max(0.0, mass - budget) / max(1, budget) / 2)

    def of(kind: DesignComponentKind) -> float:
        return ratio(parts, tough, defaults, kind)

    def mean(*kinds: DesignComponentKind) -> float:
        found = [of(kind) for kind in kinds if kind in parts]
        return fmean(found) if found else 1.0

    firepower = await mount_firepower(session, await mounts_of(session, design.id))
    armed = firepower / ARMAMENT_NORM * aim(design.fire_control) if firepower > 0 else len(spec.armament) * 15 * of(C.WEAPON)
    fixed = set(design.locked or [])
    derived = {
        "mass": round_half_up(mass),
        "speed": clamp_int(spec.speed * mean(C.PROPULSION, C.POWER) * (1 - burden), 0, 500),
        "range": clamp_int(spec.range * mean(C.HOLD, C.QUARTERS, C.NAVIGATION, C.LIFE_SUPPORT), 0, 1000),
        "seaworthiness": clamp_int(spec.endurance * mean(C.HULL, C.FRAME, C.NAVIGATION, C.WARD, C.LIFT) * (1 - burden / 2), 0, PERCENT),
        "cargo": round_half_up(spec.cargo * of(C.HOLD)),
        "armament": clamp_int(armed, 0, PERCENT),
        "crew": round_half_up(spec.crew * of(C.QUARTERS)),
        "troops": round_half_up(spec.troops * mean(C.TROOPS, C.QUARTERS)),
        "armour": clamp_int(spec.armour * of(C.ARMOUR), 0, PERCENT),
        "structure": round_half_up(spec.structure * mean(C.HULL, C.FRAME)),
    }
    for key, amount in derived.items():
        if key not in fixed:
            setattr(design, key, amount)
    await session.flush()
    return design


def catalogue_fields(spec: FrameSpec, quality: int) -> dict[str, object]:
    fuel = FUELS[spec.propulsion]
    return {
        "domain": spec.domain,
        "family": spec.family,
        "propulsion": spec.propulsion,
        "size_class": spec.size,
        "fuel": fuel,
        "fuel_use": SIZE_SCALE[spec.size] if fuel is not None else 0,
        "cost": round_half_up((spec.structure + spec.armour + spec.crew // 5 + spec.slots * 10) * (0.5 + quality / PERCENT)),
        "upkeep": max(1, SIZE_SCALE[spec.size] * (1 + spec.slots // 2)),
        "tech_level": spec.level,
        "strangeness": spec.strangeness,
    }


async def lay_sections(session: AsyncSession, design: DesignRow, sizes: dict[DesignComponentKind, int], quality: int, parent_id: int | None) -> None:
    if design.frame is None:
        return
    spec = FRAMES[design.frame]
    old = {row.section: row for row in await sections_of(session, parent_id)} if parent_id is not None else {}
    for part in LAYOUTS[spec.family]:
        before = old.get(part.section)
        session.add(
            DesignSectionRow(
                design_id=design.id,
                section=part.section,
                function=part.function,
                criticality=part.criticality,
                share=part.share,
                exposure=part.exposure,
                armour=before.armour if before is not None else (spec.armour if part.function is C.ARMOUR else spec.armour // 2),
                hazard=part.hazard,
                neighbours=[item.value for item in part.neighbours],
                material_id=before.material_id if before is not None else None,
                size=clamp_int(sizes.get(part.function, before.size if before is not None else 3), 0, FULL_SIZE),
                quality=clamp_int(quality if before is None else before.quality + REFIT_QUALITY, 0, PERCENT),
                locked=[],
            )
        )
    await session.flush()


def home_section(mount: MountKind, sections: set[VehicleSection]) -> VehicleSection | None:
    return next((place for place in (MOUNT_SECTIONS[mount], *MOUNT_FALLBACKS) if place in sections), None)


async def arm_mounts(ctx: TickContext, design: DesignRow, owner: EntityRow | None, knowledge: KnowledgeMap | None) -> None:
    if design.frame is None:
        return
    spec = FRAMES[design.frame]
    sections = {part.section for part in LAYOUTS[spec.family]}
    known = knowledge or await KnowledgeMap.load(ctx.session)
    for slot, mount in enumerate(MOUNTS[spec.family]):
        model = await mount_model(ctx, owner, mount, known)
        if model is None:
            continue
        ctx.session.add(
            DesignMountRow(
                design_id=design.id,
                slot=slot,
                mount=mount,
                section=home_section(mount, sections),
                model_id=model.id,
                count=1,
                arc=MOUNT_ARCS[mount],
                locked=[],
            )
        )
    await ctx.session.flush()


async def draw_design(
    ctx: TickContext,
    owner: EntityRow | None,
    frame: VehicleFrame,
    *,
    sizes: dict[DesignComponentKind, int] | None = None,
    quality: int = HALF,
    parent: DesignRow | None = None,
    designer_id: int | None = None,
    name: str | None = None,
    origin_id: int | None = None,
    world_id: int | None = None,
    knowledge: KnowledgeMap | None = None,
) -> DesignRow:
    spec = FRAMES[frame]
    lineage = 1 + len(await lineage_of(ctx.session, parent.id)) if parent is not None else 1
    if name is None and parent is not None:
        name = f"{parent.name.rsplit(' mark ', 1)[0]} mark {lineage}"
    row = DesignRow(
        owner_entity_id=owner.id if owner is not None else None,
        kind=spec.kind,
        frame=frame,
        name=name or await made_name(ctx.session, ctx.rules, owner, spec.label, frame.value, ctx.epoch),
        designer_entity_id=designer_id,
        parent_design_id=parent.id if parent is not None else None,
        origin_node_id=origin_id if origin_id is not None else (owner.id if owner is not None else None),
        world_id=world_id if world_id is not None else (owner.world_id if owner is not None else None),
        fire_control=parent.fire_control if parent is not None else FireControl.MANUAL,
        obsolete=False,
        epoch=ctx.epoch,
        locked=[],
        **catalogue_fields(spec, quality),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await lay_sections(ctx.session, row, sizes or frame_sizes(frame), quality, parent.id if parent is not None else None)
    needed = FAMILY_TECHNIQUES[spec.family]
    if needed is not None:
        ctx.session.add(DesignTechniqueRow(design_id=row.id, technique=needed))
    await arm_mounts(ctx, row, owner, knowledge)
    return await derive(ctx.session, ctx.rules, row)


async def lineage_of(session: AsyncSession, design_id: int) -> list[DesignRow]:
    chain: list[DesignRow] = []
    current = await session.get(DesignRow, design_id)
    while current is not None and len(chain) < PERCENT:
        chain.append(current)
        current = await session.get(DesignRow, current.parent_design_id) if current.parent_design_id is not None else None
    return chain


async def current_design(session: AsyncSession, owner_id: int, kind: DesignKind, frame: VehicleFrame | None = None) -> DesignRow | None:
    query = select(DesignRow).where(DesignRow.owner_entity_id == owner_id, DesignRow.kind == kind, DesignRow.obsolete.is_(False))
    if frame is not None:
        query = query.where(DesignRow.frame == frame)
    return await session.scalar(query.order_by(DesignRow.epoch.desc(), DesignRow.id.desc()).limit(1))


def kind_for(frame: VehicleFrame) -> DesignKind:
    return FRAMES[frame].kind


async def fit_design(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, owner_id: int | None) -> DesignRow | None:
    if owner_id is None or held(owner_id) or "design_id" in row.locked:
        return None
    design = await current_design(ctx.session, owner_id, kind_for(row.frame), row.frame)
    if design is None:
        owner = await ctx.session.get(EntityRow, owner_id)
        if owner is None:
            return None
        design = await draw_design(ctx, owner, row.frame)
    apply_design(row, design)
    return design


def apply_design(row: VesselProfileRow, design: DesignRow) -> None:
    row.design_id = design.id
    for column, value in (("seaworthiness", design.seaworthiness), ("cargo_capacity", design.cargo)):
        if column not in row.locked and value > 0:
            setattr(row, column, value)
    if design.frame is not None and "frame" not in row.locked:
        row.frame = design.frame
    if design.frame is not None and "armament" not in row.locked:
        row.armament = [item.value for item in FRAMES[design.frame].armament]


async def wear_of(session: AsyncSession, vessel_id: int, part: DesignComponentKind) -> ComponentWearRow:
    row = await session.get(ComponentWearRow, (vessel_id, part))
    if row is None:
        row = ComponentWearRow(vessel_entity_id=vessel_id, component=part, wear=0, locked=[])
        session.add(row)
        await session.flush()
    return row


async def fail(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, part: DesignComponentKind) -> None:
    if part is C.HULL:
        shift(row, "condition", -HULL_DAMAGE)
    elif part is C.PROPULSION and "status" not in row.locked:
        row.status = VesselStatus.DAMAGED
    elif part is C.HOLD:
        shift(row, "cargo_capacity", -row.cargo_capacity // 4, high=1_000_000)
    elif part is C.QUARTERS:
        shift(row, "crew", -row.crew * CREW_LOSS_PCT / PERCENT, high=1_000_000)
    elif part is C.NAVIGATION:
        row.region_entity_id = row.region_entity_id if "region_entity_id" in row.locked else None
    if row.design_id is not None:
        section = next((item for item in await sections_of(ctx.session, row.design_id) if item.function is part), None)
        if section is not None:
            await strike_vessel(ctx, vessel, row, section.section, 1)
    await note(
        ctx,
        f"{vessel.name} {FAILURE_TEXT[part]} when its {part.value.replace('_', ' ')} failed.",
        key=f"designs.failure_{part.value}",
        ids=[vessel.id],
    )


async def wear_leg(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, *, stormy: bool, tally: DesignTally) -> None:
    table = ctx.rules.designs
    if row.design_id is None or held(vessel.id):
        return
    parts = await components_of(ctx.session, row.design_id)
    for kind, part in sorted(parts.items()):
        if part.size <= 0:
            continue
        strength, _, decay = await toughness(ctx.session, part)
        wear = await wear_of(ctx.session, vessel.id, kind)
        step = (table.wear_per_leg + (table.storm_wear if stormy else 0)) * decay / max(0.25, strength)
        shift(wear, "wear", step)
        tally.worn += 1
        if wear.wear >= table.failure_at and ctx.rng(f"failure.{vessel.id}.{kind.value}.{ctx.epoch}").chance(table.failure_pct):
            await fail(ctx, vessel, row, kind)
            tally.failures += 1


async def mend(ctx: TickContext, row: VesselProfileRow, tally: DesignTally) -> int:
    if row.status is not VesselStatus.DOCKED or row.home_port_entity_id is None:
        return 0
    yard = await ctx.session.scalar(
        select(WorkshopRow).where(WorkshopRow.community_entity_id == row.home_port_entity_id, WorkshopRow.kind == WorkshopKind.SHIPYARD).limit(1)
    )
    if yard is None:
        return 0
    mended = 0
    for wear in await ctx.session.scalars(select(ComponentWearRow).where(ComponentWearRow.vessel_entity_id == row.entity_id, ComponentWearRow.wear > 0)):
        before = wear.wear
        shift(wear, "wear", -ctx.rules.designs.shipyard_repair * yard.level)
        mended += before - wear.wear
    tally.mended += mended > 0
    return mended


async def design_power(session: AsyncSession, row: VesselProfileRow) -> float:
    design = await session.get(DesignRow, row.design_id) if row.design_id is not None else None
    if design is None:
        return 1.0
    worn = await session.scalars(select(ComponentWearRow.wear).where(ComponentWearRow.vessel_entity_id == row.entity_id))
    wear = list(worn)
    fatigue = sum(wear) / max(1, len(wear)) / PERCENT
    return (1 + design.armament / PERCENT) * (1 - fatigue / 2)


async def refit(ctx: TickContext, tally: DesignTally) -> None:
    table = ctx.rules.designs
    knowledge = await KnowledgeMap.load(ctx.session)
    for design in list(await ctx.session.scalars(select(DesignRow).where(DesignRow.obsolete.is_(False)).order_by(DesignRow.id))):
        owner = await ctx.session.get(EntityRow, design.owner_entity_id) if design.owner_entity_id is not None else None
        if owner is None or held(owner.id) or design.epoch >= ctx.epoch or "obsolete" in design.locked or design.frame is None:
            continue
        if not ctx.rng(f"refit.{design.id}.{ctx.epoch}").chance(table.refit_pct):
            continue
        newer = await draw_design(ctx, owner, design.frame, parent=design, designer_id=design.designer_entity_id, knowledge=knowledge)
        design.obsolete = True
        tally.refits += 1
        await note(ctx, f"{owner.name} drew {newer.name}, an improvement on {design.name}.", key="designs.refit", ids=[owner.id])
        for vessel in await ctx.session.scalars(
            select(VesselProfileRow).where(VesselProfileRow.design_id == design.id, VesselProfileRow.status == VesselStatus.DOCKED)
        ):
            if not held(vessel.entity_id) and "design_id" not in vessel.locked:
                apply_design(vessel, newer)
