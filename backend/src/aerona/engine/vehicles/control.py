from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.vehicles import (
    GROUP_FIELDS,
    GROUP_SECTION_FIELDS,
    MOUNT_FIELDS,
    SECTION_FIELDS,
    VESSEL_SECTION_FIELDS,
    DesignMountRow,
    DesignSectionRow,
    DesignTechniqueRow,
    VehicleGroupRow,
    VehicleGroupSectionRow,
    VesselSectionRow,
)
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.integrity import Criticality, SectionHazard, SectionState
from aerona.domain.enums.vehicles import MountKind, VehicleSection, VehicleStatus
from aerona.engine.collective.designs import MOUNT_ARCS, derive, home_section
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.equipment.models import mount_model
from aerona.engine.gatherings.control import Values, allowed, found, node
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.vehicles.groups import add_vehicles, move_vehicles, repair_group

EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "design_section": (DesignSectionRow, SECTION_FIELDS, "section of a vehicle type"),
    "design_mount": (DesignMountRow, MOUNT_FIELDS, "weapon mount"),
    "vehicle_group": (VehicleGroupRow, GROUP_FIELDS, "vehicle group"),
    "vehicle_group_section": (VehicleGroupSectionRow, GROUP_SECTION_FIELDS, "section of a vehicle group"),
    "vessel_section": (VesselSectionRow, VESSEL_SECTION_FIELDS, "section of a vessel"),
}


async def design(ctx: TickContext, design_id: int) -> DesignRow:
    return await found(ctx, DesignRow, design_id, "vehicle type")


async def set_section(ctx: TickContext, design_id: int, section: VehicleSection, values: Values) -> DesignSectionRow:
    row = await ctx.session.get(DesignSectionRow, (design_id, section))
    if row is None:
        await design(ctx, design_id)
        row = DesignSectionRow(
            design_id=design_id,
            section=section,
            function=DesignComponentKind.HULL,
            criticality=Criticality.MINOR,
            share=10,
            exposure=10,
            armour=0,
            hazard=SectionHazard.NONE,
            neighbours=[],
            size=3,
            quality=50,
            locked=[],
        )
        ctx.session.add(row)
    apply(row, allowed(values, SECTION_FIELDS, "section of a vehicle type"), [])
    await ctx.session.flush()
    await derive(ctx.session, ctx.rules, await design(ctx, design_id))
    return row


async def remove_section(ctx: TickContext, design_id: int, section: VehicleSection) -> None:
    await ctx.session.delete(await found(ctx, DesignSectionRow, (design_id, section), "section of a vehicle type"))
    await ctx.session.flush()
    await derive(ctx.session, ctx.rules, await design(ctx, design_id))


async def add_mount(ctx: TickContext, design_id: int, mount: MountKind, values: Values) -> DesignMountRow:
    found_design = await design(ctx, design_id)
    sections = {row.section for row in await ctx.session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id == design_id))}
    slots = list(await ctx.session.scalars(select(DesignMountRow.slot).where(DesignMountRow.design_id == design_id)))
    owner = await ctx.session.get(EntityRow, found_design.owner_entity_id) if found_design.owner_entity_id is not None else None
    model = await mount_model(ctx, owner, mount, await KnowledgeMap.load(ctx.session))
    row = DesignMountRow(
        design_id=design_id,
        slot=max(slots, default=-1) + 1,
        mount=mount,
        section=home_section(mount, sections),
        model_id=model.id if model is not None else None,
        count=1,
        arc=MOUNT_ARCS[mount],
        locked=[],
    )
    ctx.session.add(row)
    apply(row, allowed(values, MOUNT_FIELDS, "weapon mount"), [])
    await ctx.session.flush()
    await derive(ctx.session, ctx.rules, await design(ctx, design_id))
    return row


async def add_technique(ctx: TickContext, design_id: int, technique: Technique) -> DesignTechniqueRow:
    await design(ctx, design_id)
    if await ctx.session.get(DesignTechniqueRow, (design_id, technique)) is not None:
        raise ValidationFailedError("That vehicle type already needs this technique.")
    row = DesignTechniqueRow(design_id=design_id, technique=technique)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def remove_technique(ctx: TickContext, design_id: int, technique: Technique) -> None:
    await ctx.session.delete(await found(ctx, DesignTechniqueRow, (design_id, technique), "technique of a vehicle type"))
    await ctx.session.flush()


async def new_group(ctx: TickContext, holder_id: int, design_id: int, count: int, *, crewed: int, region_id: int | None) -> VehicleGroupRow:
    await node(ctx, holder_id, "holder")
    row = await add_vehicles(ctx.session, holder_id, await design(ctx, design_id), count, epoch=ctx.epoch, crewed=crewed, region_id=region_id)
    if row is None:
        raise ValidationFailedError("A held holder cannot take vehicles.")
    await ctx.session.flush()
    return row


async def move_group(ctx: TickContext, group_id: int, holder_id: int, count: int) -> int:
    group = await found(ctx, VehicleGroupRow, group_id, "vehicle group")
    await node(ctx, holder_id, "holder")
    moved = await move_vehicles(ctx.session, group, holder_id, count, epoch=ctx.epoch)
    await ctx.session.flush()
    return moved


async def repair(ctx: TickContext, group_id: int, points: int) -> int:
    group = await found(ctx, VehicleGroupRow, group_id, "vehicle group")
    mended = await repair_group(ctx.session, group, points, yard=True)
    if group.status is VehicleStatus.WRECKED:
        group.status = VehicleStatus.READY
    await ctx.session.flush()
    return mended


async def set_group_section(ctx: TickContext, group_id: int, section: VehicleSection, values: Values) -> VehicleGroupSectionRow:
    row = await ctx.session.get(VehicleGroupSectionRow, (group_id, section))
    if row is None:
        await found(ctx, VehicleGroupRow, group_id, "vehicle group")
        row = VehicleGroupSectionRow(group_id=group_id, section=section, damaged=0, disabled=0, destroyed=0, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, GROUP_SECTION_FIELDS, "section of a vehicle group"), [])
    await ctx.session.flush()
    return row


async def set_vessel_section(ctx: TickContext, vessel_id: int, section: VehicleSection, values: Values) -> VesselSectionRow:
    row = await ctx.session.get(VesselSectionRow, (vessel_id, section))
    if row is None:
        await found(ctx, VesselProfileRow, vessel_id, "vessel")
        row = VesselSectionRow(vessel_entity_id=vessel_id, section=section, state=SectionState.SOUND, condition=100, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, VESSEL_SECTION_FIELDS, "section of a vessel"), [])
    await ctx.session.flush()
    return row


async def remove_mount(ctx: TickContext, mount_id: int) -> None:
    row = await found(ctx, DesignMountRow, mount_id, "weapon mount")
    design_id = row.design_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    await derive(ctx.session, ctx.rules, await design(ctx, design_id))


async def clear_group_section(ctx: TickContext, group_id: int, section: VehicleSection) -> None:
    await ctx.session.delete(await found(ctx, VehicleGroupSectionRow, (group_id, section), "section of a vehicle group"))
    await ctx.session.flush()


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    if isinstance(row, DesignSectionRow | DesignMountRow):
        await derive(ctx.session, ctx.rules, await design(ctx, row.design_id))
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    row = await found(ctx, table, key, label)
    design_id = row.design_id if isinstance(row, DesignSectionRow | DesignMountRow) else None
    await ctx.session.delete(row)
    await ctx.session.flush()
    if design_id is not None:
        await derive(ctx.session, ctx.rules, await design(ctx, design_id))
