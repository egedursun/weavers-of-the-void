from sqlalchemy import select

from aerona.catalog.vehicles import FRAMES, frame_layout, section_swap
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.vehicles import DesignMountRow, DesignSectionRow, VesselSectionRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.vehicles import MountArc, VehicleSection
from aerona.engine.collective.designs import MOUNT_ARCS, arm_mounts, catalogue_fields, derive, frame_sizes, home_section, lay_sections, mounts_of, sections_of
from aerona.engine.context import TickContext
from aerona.engine.equipment.models import mount_model
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.vehicles.fleet import CREW_ROLES, readings, role_design, serving
from aerona.engine.vehicles.groups import add_vehicles

FIXUP = "vehicles.made_kinds"
REARM = "vehicles.mounts_seated"
RESEAT = "vehicles.frame_sections"
DESIGN_SECTION_FIELDS = ("design_id", "function", "criticality", "share", "exposure", "armour", "hazard", "neighbours", "material_id", "size", "quality")


async def complete_designs(ctx: TickContext, knowledge: KnowledgeMap) -> int:
    filled = 0
    for design in list(await ctx.session.scalars(select(DesignRow).where(DesignRow.frame.is_not(None), DesignRow.domain.is_(None)).order_by(DesignRow.id))):
        if design.frame is None:
            continue
        spec = FRAMES[design.frame]
        for key, value in catalogue_fields(spec, design.seaworthiness or 50).items():
            if key not in (design.locked or []):
                setattr(design, key, value)
        if design.world_id is None and design.owner_entity_id is not None:
            owner = await ctx.session.get(EntityRow, design.owner_entity_id)
            design.world_id = owner.world_id if owner is not None else None
        design.origin_node_id = design.origin_node_id or design.owner_entity_id
        if not await sections_of(ctx.session, design.id):
            await lay_sections(ctx.session, design, frame_sizes(design.frame), 50, None)
        if not await mounts_of(ctx.session, design.id):
            owner = await ctx.session.get(EntityRow, design.owner_entity_id) if design.owner_entity_id is not None else None
            await arm_mounts(ctx, design, owner, knowledge)
        await derive(ctx.session, ctx.rules, design)
        filled += 1
    return filled


async def crew_armies(ctx: TickContext, knowledge: KnowledgeMap) -> int:
    granted = 0
    for army_row in list(await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))):
        army = await living_entity(ctx.session, army_row.entity_id)
        owner = await living_entity(ctx.session, army_row.owner_entity_id) if army is not None else None
        if army is None or owner is None or held(army.id) or army.status is not EntityStatus.CANON:
            continue
        stacks = list(await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army.id, ArmyUnitRow.count > 0)))
        for stack in stacks:
            if stack.kind not in CREW_ROLES:
                continue
            if any(serving(reading, stack.kind) for reading in await readings(ctx.session, army.id)):
                continue
            design = await role_design(ctx, owner, stack.kind, knowledge)
            if design is None:
                continue
            count = max(1, stack.count // max(1, design.crew))
            await add_vehicles(ctx.session, army.id, design, count, epoch=ctx.epoch, crewed=count, region_id=army.location_id)
            granted += count
    return granted


async def rearm(ctx: TickContext, knowledge: KnowledgeMap) -> dict[str, int]:
    tally = {"armed": 0, "seated": 0, "aimed": 0, "struck": 0}
    for row in list(await ctx.session.scalars(select(DesignMountRow).order_by(DesignMountRow.id))):
        found = await ctx.session.get(DesignRow, row.design_id)
        if found is None or found.frame is None:
            continue
        owner = await ctx.session.get(EntityRow, found.owner_entity_id) if found.owner_entity_id is not None else None
        if owner is not None and held(owner.id):
            continue
        locked = set(row.locked or [])
        if row.model_id is None and "model_id" not in locked:
            model = await mount_model(ctx, owner, row.mount, knowledge)
            if model is None:
                await ctx.session.delete(row)
                tally["struck"] += 1
                continue
            row.model_id = model.id
            tally["armed"] += 1
        if row.section is None and "section" not in locked:
            row.section = home_section(row.mount, {part.section for part in frame_layout(found.frame)})
            tally["seated"] += row.section is not None
        if row.arc is MountArc.ALL_ROUND and "arc" not in locked and MOUNT_ARCS[row.mount] is not MountArc.ALL_ROUND:
            row.arc = MOUNT_ARCS[row.mount]
            tally["aimed"] += 1
    await ctx.session.flush()
    for found in list(await ctx.session.scalars(select(DesignRow).where(DesignRow.frame.is_not(None)).order_by(DesignRow.id))):
        await derive(ctx.session, ctx.rules, found)
    return tally


async def reseat_sections(ctx: TickContext) -> int:
    moved = 0
    for design in list(await ctx.session.scalars(select(DesignRow).where(DesignRow.frame.is_not(None)).order_by(DesignRow.id))):
        swap = section_swap(design.frame) if design.frame is not None else {}
        rows = list(await ctx.session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id == design.id)))
        present = {row.section for row in rows}
        for row in rows:
            row.neighbours = [str(found) for item in row.neighbours if (found := swap.get(VehicleSection(item), VehicleSection(item))) is not None]
            if row.section not in swap:
                continue
            target = swap[row.section]
            await ctx.session.delete(row)
            if target is not None and target not in present:
                ctx.session.add(DesignSectionRow(**{**{key: getattr(row, key) for key in DESIGN_SECTION_FIELDS}, "section": target}))
            moved += 1
    for vessel in list(await ctx.session.scalars(select(VesselProfileRow).order_by(VesselProfileRow.entity_id))):
        swap = section_swap(vessel.frame)
        laid_rows = list(await ctx.session.scalars(select(VesselSectionRow).where(VesselSectionRow.vessel_entity_id == vessel.entity_id)))
        present = {laid.section for laid in laid_rows}
        for laid in laid_rows:
            if laid.section not in swap:
                continue
            target = swap[laid.section]
            await ctx.session.delete(laid)
            if target is not None and target not in present:
                ctx.session.add(
                    VesselSectionRow(
                        vessel_entity_id=laid.vessel_entity_id, section=target, state=laid.state, condition=laid.condition, locked=list(laid.locked)
                    )
                )
            moved += 1
    await ctx.session.flush()
    return moved


async def made_kinds_fixup(ctx: TickContext) -> dict[str, int]:
    result: dict[str, int] = {}
    knowledge = await KnowledgeMap.load(ctx.session)
    if await ctx.session.get(AppliedFixupRow, FIXUP) is None:
        result = {"designs": await complete_designs(ctx, knowledge), "vehicles": await crew_armies(ctx, knowledge)}
        ctx.session.add(AppliedFixupRow(key=FIXUP, result=result))
    if await ctx.session.get(AppliedFixupRow, REARM) is None:
        seated = await rearm(ctx, knowledge)
        ctx.session.add(AppliedFixupRow(key=REARM, result=seated))
        result |= seated
    if await ctx.session.get(AppliedFixupRow, RESEAT) is None:
        reseated = {"reseated": await reseat_sections(ctx)}
        ctx.session.add(AppliedFixupRow(key=RESEAT, result=reseated))
        result |= reseated
    return result
