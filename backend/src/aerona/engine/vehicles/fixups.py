from sqlalchemy import select

from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.collective.designs import arm_mounts, catalogue_fields, derive, frame_sizes, lay_sections, mounts_of, sections_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.vehicles.fleet import CREW_ROLES, readings, role_design, serving
from aerona.engine.vehicles.groups import add_vehicles

FIXUP = "vehicles.made_kinds"


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


async def made_kinds_fixup(ctx: TickContext) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, FIXUP) is not None:
        return {}
    knowledge = await KnowledgeMap.load(ctx.session)
    result = {"designs": await complete_designs(ctx, knowledge), "vehicles": await crew_armies(ctx, knowledge)}
    ctx.session.add(AppliedFixupRow(key=FIXUP, result=result))
    return result
