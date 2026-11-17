from collections import Counter

from fastapi import APIRouter, Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.structures import (
    ConstructionView,
    DesignView,
    FunctionBreakdownView,
    KindOptionView,
    SettlementStructuresView,
    StructureView,
)
from aerona.catalog.materials import MATERIALS
from aerona.catalog.structure_effects import STRUCTURE_OWN_EFFECTS
from aerona.catalog.structures import STRUCTURES
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.economy import NodeMaterialRow, WorkshopRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import ConstructionRow, StructureDesignRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.structure import BuildScale, ConstructionState
from aerona.engine.primitives.stats import stat_or
from aerona.engine.structures.profiles import condition_factor
from aerona.engine.structures.spec import Resolved, build_cost, resolve, slots_for, tier_allows
from aerona.rules.registry import Rules

router = APIRouter(tags=["structures"])


async def rules_of(session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).require_cosmos()
    return rules_from_snapshot(cosmos.rules_snapshot)


async def name_of(session: AsyncSession, node_id: int | None) -> str | None:
    if node_id is None:
        return None
    node = await session.get(NodeRow, node_id)
    return str(getattr(node, "name", None)) if node is not None else None


def breakdown(rules: Rules, work: EntityRow, profile: StructureProfileRow, resolved: Resolved) -> FunctionBreakdownView:
    ley = rules.structure_functions.ley_bonus_pct if profile.on_ley_line and resolved.ley else 0
    return FunctionBreakdownView(
        base=stat_or(work, "function", rules.deep_life.structure_function_base),
        design_pct=resolved.function_pct,
        condition_pct=round(condition_factor(rules, profile.condition) * PERCENT),
        staff_pct=profile.staff_pct,
        ley_pct=PERCENT + ley,
        effect_pct=profile.effect_pct,
        threshold=rules.structure_functions.condition_threshold,
    )


def construction_view(rules: Rules, row: ConstructionRow | None) -> ConstructionView | None:
    if row is None:
        return None
    wonder = resolve(row.kind).scale is BuildScale.WONDER
    return ConstructionView(
        id=row.id,
        status=row.status,
        cost=row.cost,
        work=row.progress,
        percent=min(PERCENT, round(row.progress * PERCENT / max(1, row.cost))),
        funds=row.funds,
        workers=row.workers,
        materials_pct=row.materials_pct,
        stalled_epochs=row.stalled_epochs,
        stall_limit=rules.construction.wonder_stall_epochs if wonder else rules.construction.stall_epochs,
        generations=row.generations,
        started_epoch=row.started_epoch,
        finished_epoch=row.finished_epoch,
        player=row.player,
        locked=list(row.locked),
    )


async def material_of(session: AsyncSession, structure_id: int) -> tuple[NodeMaterialRow | None, str | None]:
    row = await session.get(NodeMaterialRow, (structure_id, MaterialSlot.BODY))
    if row is None:
        return None, None
    if row.world_material_id is not None:
        world = await session.get(WorldMaterialRow, row.world_material_id)
        return row, world.name if world is not None else None
    return row, MATERIALS[row.material].label if row.material is not None else None


async def structure_view(session: AsyncSession, rules: Rules, work: EntityRow, profile: StructureProfileRow) -> StructureView:
    design = await session.get(StructureDesignRow, profile.design_id) if profile.design_id is not None else None
    resolved = resolve(profile.kind, design)
    staff = await session.scalar(select(StructureStaffRow).where(StructureStaffRow.structure_entity_id == work.id).limit(1))
    construction = await session.scalar(
        select(ConstructionRow).where(ConstructionRow.structure_entity_id == work.id).order_by(ConstructionRow.id.desc()).limit(1)
    )
    workshop = await session.scalar(select(WorkshopRow.kind).where(WorkshopRow.structure_entity_id == work.id).limit(1))
    material, material_label = await material_of(session, work.id)
    return StructureView(
        id=work.id,
        name=work.name,
        status=work.status,
        kind=profile.kind,
        group=resolved.group,
        label=resolved.label,
        design_id=profile.design_id,
        design_name=design.name if design is not None else None,
        level=profile.level,
        capacity=profile.capacity,
        capacity_unit=resolved.capacity_unit,
        condition=profile.condition,
        durability=stat_or(work, "durability", PERCENT),
        construction_state=profile.construction_state,
        progress=profile.progress,
        fire_resistance=profile.fire_resistance,
        material=material.material if material is not None else None,
        world_material_id=material.world_material_id if material is not None else None,
        material_label=material_label,
        host_id=profile.host_entity_id,
        host_name=await name_of(session, profile.host_entity_id),
        builder_id=profile.builder_entity_id,
        builder_name=await name_of(session, profile.builder_entity_id),
        builder_kind=profile.builder_kind,
        architect_id=profile.architect_entity_id,
        architect_name=await name_of(session, profile.architect_entity_id),
        dedicated_son_id=profile.dedicated_son_id,
        dedicated_son_name=await name_of(session, profile.dedicated_son_id),
        style_ornament=profile.style_ornament,
        style_geometry=profile.style_geometry,
        style_colour=profile.style_colour,
        style_scale=profile.style_scale,
        style_symmetry=profile.style_symmetry,
        on_ley_line=profile.on_ley_line,
        attuned=resolved.ley,
        anchor=profile.anchor,
        own_effects=list(STRUCTURE_OWN_EFFECTS[profile.kind]),
        splendor=stat_or(work, "splendor", 0),
        function=stat_or(work, "function", 0),
        effect_pct=profile.effect_pct,
        staff_pct=profile.staff_pct,
        staff_class=resolved.staff_class,
        staff_required=staff.required if staff is not None else 0,
        staff_allocated=staff.allocated if staff is not None else 0,
        staff_held=staff.held if staff is not None else False,
        upkeep_coin=profile.upkeep_coin,
        upkeep_goods=profile.upkeep_goods,
        upkeep_commodity=resolved.upkeep_commodity,
        unpaid_epochs=profile.unpaid_epochs,
        built_epoch=profile.built_epoch,
        workshop=workshop,
        min_tier=resolved.min_tier,
        scale=resolved.scale,
        locked=list(profile.locked),
        breakdown=breakdown(rules, work, profile, resolved),
        construction=construction_view(rules, construction),
    )


async def design_views(session: AsyncSession, world_id: int | None) -> list[DesignView]:
    used = Counter(
        {
            design_id: count
            for design_id, count in await session.execute(
                select(StructureProfileRow.design_id, func.count()).where(StructureProfileRow.design_id.is_not(None)).group_by(StructureProfileRow.design_id)
            )
            if design_id is not None
        }
    )
    statement = select(StructureDesignRow).order_by(StructureDesignRow.id)
    if world_id is not None:
        statement = statement.where((StructureDesignRow.world_id == world_id) | StructureDesignRow.world_id.is_(None))
    return [
        DesignView(
            id=row.id,
            world_id=row.world_id,
            name=row.name,
            description=row.description,
            base_kind=row.base_kind,
            staff_class=row.staff_class,
            staff_scale=row.staff_scale,
            scale=row.scale,
            upkeep_commodity=row.upkeep_commodity,
            min_tier=row.min_tier,
            ley=row.ley,
            capacity_pct=row.capacity_pct,
            cost_pct=row.cost_pct,
            upkeep_pct=row.upkeep_pct,
            function_pct=row.function_pct,
            staff_pct=row.staff_pct,
            retired=row.retired,
            used_by=used.get(row.id, 0),
            locked=list(row.locked),
        )
        for row in await session.scalars(statement)
    ]


@router.get("/entities/{entity_id}/structures", response_model=SettlementStructuresView)
async def host_structures(services: ServicesDep, entity_id: int = Path(ge=1)) -> SettlementStructuresView:
    async with reader(services) as session:
        rules = await rules_of(session)
        host = await session.get(EntityRow, entity_id)
        if host is None or host.entity_type not in COMMUNITY_TYPES:
            raise NotFoundError("No such settlement or people.")
        rows = (
            await session.execute(
                select(EntityRow, StructureProfileRow)
                .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
                .where(StructureProfileRow.host_entity_id == host.id)
                .order_by(EntityRow.id)
            )
        ).all()
        structures = [await structure_view(session, rules, work, profile) for work, profile in rows]
        town = await session.get(SettlementProfileRow, host.id)
        tier = town.size_tier if town is not None else None
        present = Counter(item.kind for item in structures if item.construction_state is not ConstructionState.RUINED)
        kinds = [
            KindOptionView(
                kind=kind,
                group=spec.group,
                label=spec.label,
                min_tier=spec.min_tier,
                allowed=tier is None or tier_allows(tier, resolve(kind)),
                scale=spec.scale,
                cost=build_cost(rules, resolve(kind), 1),
                capacity_unit=spec.capacity,
                staff_class=spec.staff,
                staff_scale=spec.staff_scale,
                present=present.get(kind, 0),
            )
            for kind, spec in STRUCTURES.items()
        ]
        return SettlementStructuresView(
            host_id=host.id,
            world_id=host.world_id,
            size_tier=tier,
            slots_total=slots_for(rules, tier) if tier is not None else rules.construction.slots_base,
            slots_used=sum(present.values()),
            structures=structures,
            kinds=kinds,
            designs=await design_views(session, host.world_id),
        )


@router.get("/entities/{entity_id}/structure", response_model=StructureView)
async def one_structure(services: ServicesDep, entity_id: int = Path(ge=1)) -> StructureView:
    async with reader(services) as session:
        rules = await rules_of(session)
        work = await session.get(EntityRow, entity_id)
        profile = await session.get(StructureProfileRow, entity_id)
        if work is None or work.entity_type is not EntityType.STRUCTURE or profile is None:
            raise NotFoundError("This structure is surveyed at the next epoch.")
        return await structure_view(session, rules, work, profile)
