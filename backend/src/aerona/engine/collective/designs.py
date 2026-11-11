from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.vessels import HULLS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.collective import ComponentWearRow, DesignComponentRow, DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.economy import WorkshopRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import DesignComponentKind, DesignKind
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.military import HullClass, VesselStatus
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

C = DesignComponentKind
FULL_SIZE = 10
TOUGH = 50
VESSEL_PARTS = (C.HULL, C.PROPULSION, C.HOLD, C.QUARTERS, C.ARMOUR, C.WEAPON, C.WARD, C.NAVIGATION)
ENGINE_PARTS = (C.FRAME, C.COUNTERWEIGHT, C.WEAPON, C.ARMOUR)
PARTS = total(DesignKind, {DesignKind.VESSEL: VESSEL_PARTS, DesignKind.SKYSHIP: VESSEL_PARTS, DesignKind.SIEGE_ENGINE: ENGINE_PARTS})
FAILURE_TEXT = MappingProxyType(
    {
        C.HULL: "sprang a leak",
        C.PROPULSION: "lost its means of moving",
        C.HOLD: "lost part of its cargo",
        C.QUARTERS: "lost crew to sickness and cold",
        C.NAVIGATION: "lost its way",
        C.ARMOUR: "had its armour give way",
        C.WEAPON: "had its weapons fail",
        C.WARD: "had its wards falter",
    }
)
REFIT_QUALITY = 10
HULL_DAMAGE = 20
CREW_LOSS_PCT = 10
FIELD_UNIT = 10


@dataclass
class DesignTally:
    drawn: int = 0
    refits: int = 0
    worn: int = 0
    failures: int = 0
    mended: int = 0


async def components_of(session: AsyncSession, design_id: int) -> dict[DesignComponentKind, DesignComponentRow]:
    rows = await session.scalars(select(DesignComponentRow).where(DesignComponentRow.design_id == design_id))
    return {row.component: row for row in rows}


async def toughness(session: AsyncSession, part: DesignComponentRow) -> tuple[float, float, float]:
    material = await session.get(WorldMaterialRow, part.material_id) if part.material_id is not None else None
    if material is None:
        return 1.0, 1.0, 1.0
    return material.toughness / TOUGH, material.weight / TOUGH, 1 + material.decay / PERCENT


def worth(part: DesignComponentRow | None, tough: float = 1.0) -> float:
    return part.size * part.quality / PERCENT * tough if part is not None else 0.0


async def derive(session: AsyncSession, rules: Rules, design: DesignRow) -> DesignRow:
    parts = await components_of(session, design.id)
    tough: dict[DesignComponentKind, float] = {}
    mass = 0.0
    for kind, part in parts.items():
        strength, weight, _ = await toughness(session, part)
        tough[kind] = strength
        mass += part.size * weight
    budget = rules.designs.mass_budget
    burden = max(0.0, mass - budget) / max(1, budget)

    def value(kind: DesignComponentKind) -> float:
        return worth(parts.get(kind), tough.get(kind, 1.0))

    fixed = set(design.locked or [])
    derived = {
        "mass": round_half_up(mass),
        "speed": clamp_int((value(C.PROPULSION) * FIELD_UNIT - mass) * (1 - burden), 0, PERCENT),
        "range": clamp_int((value(C.HOLD) + value(C.QUARTERS) + value(C.NAVIGATION)) * FIELD_UNIT / 3, 0, PERCENT),
        "seaworthiness": clamp_int((value(C.HULL) * 2 + value(C.NAVIGATION) + value(C.WARD)) * FIELD_UNIT / 4 * (1 - burden / 2), 0, PERCENT),
        "cargo": round_half_up(value(C.HOLD) * FIELD_UNIT * 2),
        "armament": clamp_int((value(C.WEAPON) * 2 + value(C.ARMOUR) + value(C.COUNTERWEIGHT) + value(C.FRAME)) * FIELD_UNIT / 3, 0, PERCENT),
        "crew": round_half_up(value(C.QUARTERS) * FIELD_UNIT),
    }
    for key, amount in derived.items():
        if key not in fixed:
            setattr(design, key, amount)
    await session.flush()
    return design


async def draw_design(
    ctx: TickContext,
    owner: EntityRow,
    kind: DesignKind,
    *,
    hull: HullClass | None = None,
    sizes: dict[DesignComponentKind, int] | None = None,
    quality: int = PERCENT // 2,
    parent: DesignRow | None = None,
    designer_id: int | None = None,
    name: str | None = None,
) -> DesignRow:
    lineage = 1
    if parent is not None:
        lineage = 1 + len(await lineage_of(ctx.session, parent.id))
    row = DesignRow(
        owner_entity_id=owner.id,
        kind=kind,
        hull=hull,
        name=name or f"{owner.name} {(hull.value if hull is not None else kind.value).replace('_', ' ')} mark {lineage}",
        designer_entity_id=designer_id,
        parent_design_id=parent.id if parent is not None else None,
        obsolete=False,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    given = sizes or {}
    old = await components_of(ctx.session, parent.id) if parent is not None else {}
    for part in PARTS[kind]:
        before = old.get(part)
        ctx.session.add(
            DesignComponentRow(
                design_id=row.id,
                component=part,
                material_id=before.material_id if before is not None else None,
                size=clamp_int(given.get(part, before.size if before is not None else 3), 0, FULL_SIZE),
                quality=clamp_int(quality if before is None else before.quality + REFIT_QUALITY, 0, PERCENT),
            )
        )
    await ctx.session.flush()
    return await derive(ctx.session, ctx.rules, row)


async def lineage_of(session: AsyncSession, design_id: int) -> list[DesignRow]:
    chain: list[DesignRow] = []
    current = await session.get(DesignRow, design_id)
    while current is not None and len(chain) < PERCENT:
        chain.append(current)
        current = await session.get(DesignRow, current.parent_design_id) if current.parent_design_id is not None else None
    return chain


def hull_sizes(hull: HullClass) -> dict[DesignComponentKind, int]:
    spec = HULLS[hull]
    return {
        C.HULL: clamp_int(spec.seaworthiness // FIELD_UNIT, 1, FULL_SIZE),
        C.PROPULSION: clamp_int(spec.speed // FIELD_UNIT, 1, FULL_SIZE),
        C.HOLD: clamp_int(spec.cargo // (FIELD_UNIT * 2), 1, FULL_SIZE),
        C.QUARTERS: clamp_int(spec.crew // FIELD_UNIT, 1, FULL_SIZE),
        C.WEAPON: clamp_int(spec.slots * 2, 0, FULL_SIZE),
        C.ARMOUR: clamp_int(spec.slots, 0, FULL_SIZE),
        C.WARD: 1 if spec.strangeness else 0,
        C.NAVIGATION: clamp_int(spec.range // FIELD_UNIT, 1, FULL_SIZE),
    }


async def current_design(session: AsyncSession, owner_id: int, kind: DesignKind, hull: HullClass | None = None) -> DesignRow | None:
    query = select(DesignRow).where(DesignRow.owner_entity_id == owner_id, DesignRow.kind == kind, DesignRow.obsolete.is_(False))
    if hull is not None:
        query = query.where(DesignRow.hull == hull)
    return await session.scalar(query.order_by(DesignRow.epoch.desc(), DesignRow.id.desc()).limit(1))


def kind_for(hull: HullClass) -> DesignKind:
    return DesignKind.SKYSHIP if HULLS[hull].sky else DesignKind.VESSEL


async def fit_design(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, owner_id: int | None) -> DesignRow | None:
    if owner_id is None or held(owner_id) or "design_id" in row.locked:
        return None
    kind = kind_for(row.hull_class)
    design = await current_design(ctx.session, owner_id, kind, row.hull_class)
    if design is None:
        owner = await ctx.session.get(EntityRow, owner_id)
        if owner is None:
            return None
        design = await draw_design(ctx, owner, kind, hull=row.hull_class, sizes=hull_sizes(row.hull_class))
    apply_design(row, design)
    return design


def apply_design(row: VesselProfileRow, design: DesignRow) -> None:
    row.design_id = design.id
    for column, value in (("seaworthiness", design.seaworthiness), ("cargo_capacity", design.cargo)):
        if column not in row.locked and value > 0:
            setattr(row, column, value)


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
    await note(
        ctx,
        f"{vessel.name} {FAILURE_TEXT.get(part, 'suffered a breakdown')} when its {part.value} failed.",
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


async def siege_design_factor(session: AsyncSession, owner_id: int | None) -> float:
    design = await current_design(session, owner_id, DesignKind.SIEGE_ENGINE) if owner_id is not None else None
    return 1 + design.armament / (PERCENT * 2) if design is not None else 1.0


async def refit(ctx: TickContext, tally: DesignTally) -> None:
    table = ctx.rules.designs
    for design in list(await ctx.session.scalars(select(DesignRow).where(DesignRow.obsolete.is_(False)).order_by(DesignRow.id))):
        owner = await ctx.session.get(EntityRow, design.owner_entity_id)
        if owner is None or held(owner.id) or design.epoch >= ctx.epoch or "obsolete" in design.locked:
            continue
        if not ctx.rng(f"refit.{design.id}.{ctx.epoch}").chance(table.refit_pct):
            continue
        newer = await draw_design(ctx, owner, design.kind, hull=design.hull, parent=design, designer_id=design.designer_entity_id)
        design.obsolete = True
        tally.refits += 1
        await note(ctx, f"{owner.name} drew {newer.name}, an improvement on {design.name}.", key="designs.refit", ids=[owner.id])
        for vessel in await ctx.session.scalars(
            select(VesselProfileRow).where(VesselProfileRow.design_id == design.id, VesselProfileRow.status == VesselStatus.DOCKED)
        ):
            if not held(vessel.entity_id) and "design_id" not in vessel.locked:
                apply_design(vessel, newer)
