from collections import defaultdict
from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.made_kinds import (
    AttractionView,
    BeingWoundsView,
    BuildingTypeView,
    CarriedView,
    CookingView,
    DesignSectionView,
    DishView,
    EquipmentModelView,
    GroupSectionView,
    IngredientView,
    KindRef,
    LoadoutView,
    MegastructureView,
    MountView,
    OwnKindsView,
    StackKitView,
    StoreView,
    StructureSectionView,
    ThingKindsView,
    UnitTypeView,
    VehicleGroupView,
    VehicleSectionView,
    VehicleTypeView,
    VesselSectionView,
    WorldKindsView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.equipment import FAMILIES
from aerona.catalog.structure_sections import LAYOUTS as STRUCTURE_LAYOUTS
from aerona.catalog.structures import MEGASTRUCTURES, STRUCTURES
from aerona.catalog.units import UNITS
from aerona.catalog.vehicles import FRAMES
from aerona.catalog.vehicles import LAYOUTS as VEHICLE_LAYOUTS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import ArmyUnitEquipmentRow, EquipmentModelRow, EquipmentStoreRow, UnitDesignEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.integrity import MegastructureRow, StructureDesignSectionRow, StructureSectionRow
from aerona.db.tables.military import ArmyUnitRow, UnitDesignRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.tables.vehicles import DesignMountRow, DesignSectionRow, DesignTechniqueRow, VehicleGroupRow, VehicleGroupSectionRow, VesselSectionRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import InjuryState
from aerona.domain.enums.integrity import Criticality, SectionState
from aerona.domain.enums.mortal import MortalSex
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.decline import decline_severity
from aerona.engine.cosmos.being_wounds import VAST, can_roam, can_see, effective_might
from aerona.engine.equipment.models import MOUNT_FAMILIES
from aerona.engine.primitives.stats import stat
from aerona.engine.vehicles.fleet import army_pace
from aerona.engine.vehicles.groups import read
from aerona.rules.registry import Rules

router = APIRouter(tags=["made_kinds"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


async def material_names(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = sorted({value for value in ids if value is not None})
    if not wanted:
        return {}
    rows = await session.scalars(select(WorldMaterialRow).where(WorldMaterialRow.id.in_(wanted)))
    return {row.id: row.name or row.family.value for row in rows}


def grouped[Row](rows: Iterable[Row], key: str) -> dict[int, list[Row]]:
    found: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        found[getattr(row, key)].append(row)
    return found


async def vehicle_types(session: AsyncSession, designs: list[DesignRow]) -> list[VehicleTypeView]:
    ids = [row.id for row in designs]
    sections = grouped(
        await session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id.in_(ids)).order_by(DesignSectionRow.section)), "design_id"
    )
    mounts = grouped(
        await session.scalars(select(DesignMountRow).where(DesignMountRow.design_id.in_(ids)).order_by(DesignMountRow.slot, DesignMountRow.id)), "design_id"
    )
    techniques = grouped(await session.scalars(select(DesignTechniqueRow).where(DesignTechniqueRow.design_id.in_(ids))), "design_id")
    built_rows = await session.execute(
        select(VehicleGroupRow.design_id, func.sum(VehicleGroupRow.count)).where(VehicleGroupRow.design_id.in_(ids)).group_by(VehicleGroupRow.design_id)
    )
    built = {design_id: int(total or 0) for design_id, total in built_rows}
    materials = await material_names(session, [section.material_id for rows in sections.values() for section in rows])
    model_ids = [mount.model_id for rows in mounts.values() for mount in rows if mount.model_id is not None]
    models = {row.id: row.name for row in await session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.id.in_(model_ids)))} if model_ids else {}
    refs = await refs_of(session, [item for row in designs for item in (row.origin_node_id, row.owner_entity_id, row.designer_entity_id)])
    return [
        VehicleTypeView(
            id=row.id,
            entity_id=row.entity_id,
            name=row.name,
            description=row.description,
            world_id=row.world_id,
            origin=at(refs, row.origin_node_id),
            owner=at(refs, row.owner_entity_id),
            designer=at(refs, row.designer_entity_id),
            kind=row.kind,
            frame=row.frame,
            frame_label=FRAMES[row.frame].label if row.frame is not None else None,
            domain=row.domain,
            family=row.family,
            propulsion=row.propulsion,
            size_class=row.size_class,
            mass=row.mass,
            speed=row.speed,
            range=row.range,
            seaworthiness=row.seaworthiness,
            cargo=row.cargo,
            armament=row.armament,
            crew=row.crew,
            troops=row.troops,
            armour=row.armour,
            structure=row.structure,
            fuel=row.fuel,
            fuel_use=row.fuel_use,
            cost=row.cost,
            upkeep=row.upkeep,
            tech_level=row.tech_level,
            strangeness=row.strangeness,
            fire_control=row.fire_control,
            parent_design_id=row.parent_design_id,
            obsolete=row.obsolete,
            epoch=row.epoch,
            built=built.get(row.id, 0),
            sections=[
                VehicleSectionView(
                    section=part.section,
                    function=part.function,
                    criticality=part.criticality,
                    share=part.share,
                    exposure=part.exposure,
                    armour=part.armour,
                    hazard=part.hazard,
                    neighbours=list(part.neighbours),
                    material_id=part.material_id,
                    material_name=materials.get(part.material_id) if part.material_id is not None else None,
                    size=part.size,
                    quality=part.quality,
                    locked=list(part.locked),
                )
                for part in sections.get(row.id, [])
            ],
            mounts=[
                MountView(
                    id=mount.id,
                    slot=mount.slot,
                    mount=mount.mount,
                    section=mount.section,
                    model_id=mount.model_id,
                    model_name=models.get(mount.model_id) if mount.model_id is not None else None,
                    count=mount.count,
                    arc=mount.arc,
                    families=list(MOUNT_FAMILIES[mount.mount]),
                    locked=list(mount.locked),
                )
                for mount in mounts.get(row.id, [])
            ],
            techniques=sorted(item.technique for item in techniques.get(row.id, [])),
            locked=list(row.locked),
        )
        for row in designs
    ]


async def unit_types(session: AsyncSession, designs: list[UnitDesignRow]) -> list[UnitTypeView]:
    ids = [row.id for row in designs]
    loadouts = grouped(await session.scalars(select(UnitDesignEquipmentRow).where(UnitDesignEquipmentRow.design_id.in_(ids))), "design_id")
    techniques = grouped(await session.scalars(select(UnitDesignTechniqueRow).where(UnitDesignTechniqueRow.design_id.in_(ids))), "design_id")
    model_ids = sorted({item.model_id for rows in loadouts.values() for item in rows})
    models = {row.id: row for row in await session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.id.in_(model_ids)))} if model_ids else {}
    fielded_rows = await session.execute(
        select(ArmyUnitRow.design_id, func.sum(ArmyUnitRow.count)).where(ArmyUnitRow.design_id.in_(ids)).group_by(ArmyUnitRow.design_id)
    )
    fielded = {design_id: int(total or 0) for design_id, total in fielded_rows}
    vehicle_ids = [row.vehicle_design_id for row in designs if row.vehicle_design_id is not None]
    vehicles = {row.id: row.name for row in await session.scalars(select(DesignRow).where(DesignRow.id.in_(vehicle_ids)))} if vehicle_ids else {}
    refs = await refs_of(session, [item for row in designs for item in (row.origin_node_id, row.owner_entity_id, row.mount_species_id)])
    return [
        UnitTypeView(
            id=row.id,
            entity_id=row.entity_id,
            name=row.name,
            description=row.description,
            world_id=row.world_id,
            origin=at(refs, row.origin_node_id),
            owner=at(refs, row.owner_entity_id),
            base_kind=row.base_kind,
            role_label=UNITS[row.base_kind].label,
            family=row.family,
            melee=row.melee,
            missile=row.missile,
            defence=row.defence,
            speed=row.speed,
            mass=row.mass,
            cost=row.cost,
            upkeep=row.upkeep,
            armour=row.armour,
            shield=row.shield,
            terror=row.terror,
            counters_charge=row.counters_charge,
            flying=row.flying,
            social_class=row.social_class,
            reach=row.reach,
            volleys=row.volleys,
            accuracy=row.accuracy,
            piercing=row.piercing,
            doctrine=row.doctrine,
            formation=row.formation,
            discipline=row.discipline,
            training_epochs=row.training_epochs,
            mount_species=at(refs, row.mount_species_id),
            vehicle_design_id=row.vehicle_design_id,
            vehicle_design_name=vehicles.get(row.vehicle_design_id) if row.vehicle_design_id is not None else None,
            crew_per_vehicle=row.crew_per_vehicle,
            parent_design_id=row.parent_design_id,
            retired=row.retired,
            created_epoch=row.created_epoch,
            fielded=fielded.get(row.id, 0),
            loadout=[
                LoadoutView(
                    model_id=item.model_id,
                    model_name=models[item.model_id].name,
                    family=models[item.model_id].family,
                    slot=models[item.model_id].slot,
                    count=item.count,
                )
                for item in loadouts.get(row.id, [])
                if item.model_id in models
            ],
            techniques=sorted(item.technique for item in techniques.get(row.id, [])),
            locked=list(row.locked),
        )
        for row in designs
    ]


async def equipment_models(session: AsyncSession, models: list[EquipmentModelRow]) -> list[EquipmentModelView]:
    ids = [row.id for row in models]
    stored_rows = await session.execute(
        select(EquipmentStoreRow.model_id, func.sum(EquipmentStoreRow.count)).where(EquipmentStoreRow.model_id.in_(ids)).group_by(EquipmentStoreRow.model_id)
    )
    stored = {model_id: int(total or 0) for model_id, total in stored_rows}
    carried_rows = await session.execute(
        select(ArmyUnitEquipmentRow.model_id, func.sum(ArmyUnitEquipmentRow.count))
        .where(ArmyUnitEquipmentRow.model_id.in_(ids))
        .group_by(ArmyUnitEquipmentRow.model_id)
    )
    carried = {model_id: int(total or 0) for model_id, total in carried_rows}
    materials = await material_names(session, [row.world_material_id for row in models])
    refs = await refs_of(session, [row.origin_node_id for row in models])
    return [
        EquipmentModelView(
            id=row.id,
            entity_id=row.entity_id,
            name=row.name,
            description=row.description,
            world_id=row.world_id,
            origin=at(refs, row.origin_node_id),
            slot=row.slot,
            family=row.family,
            family_label=FAMILIES[row.family].label,
            material=row.material,
            world_material_id=row.world_material_id,
            material_name=materials.get(row.world_material_id) if row.world_material_id is not None else None,
            quality=row.quality,
            technique=row.technique,
            tech_level=row.tech_level,
            damage=row.damage,
            piercing=row.piercing,
            reach=row.reach,
            rate=row.rate,
            accuracy=row.accuracy,
            damage_type=row.damage_type,
            ammunition=row.ammunition,
            crew=row.crew,
            protection=row.protection,
            coverage=row.coverage,
            weight=row.weight,
            cost=row.cost,
            renown=row.renown,
            parent_model_id=row.parent_model_id,
            created_epoch=row.created_epoch,
            retired=row.retired,
            stored=stored.get(row.id, 0),
            carried=carried.get(row.id, 0),
            locked=list(row.locked),
        )
        for row in models
    ]


def cooking_view(row: CommunityDishRow, refs: dict[int, NodeRef], names: dict[int, str]) -> CookingView:
    community = refs.get(row.community_entity_id) or NodeRef(id=row.community_entity_id, kind=NodeKind.ENTITY, name="a lost community")
    return CookingView(
        community=community,
        dish_id=row.dish_id,
        dish_name=names.get(row.dish_id, "a lost dish"),
        popularity=row.popularity,
        cooked=row.cooked,
        since_epoch=row.since_epoch,
        locked=list(row.locked),
    )


async def dishes(session: AsyncSession, rows: list[DishRow]) -> list[DishView]:
    ids = [row.id for row in rows]
    ingredients = grouped(
        await session.scalars(select(DishIngredientRow).where(DishIngredientRow.dish_id.in_(ids)).order_by(DishIngredientRow.share.desc())), "dish_id"
    )
    cooked = grouped(
        await session.scalars(select(CommunityDishRow).where(CommunityDishRow.dish_id.in_(ids)).order_by(CommunityDishRow.popularity.desc())), "dish_id"
    )
    refs = await refs_of(session, [*(row.origin_node_id for row in rows), *(item.community_entity_id for items in cooked.values() for item in items)])
    names = {row.id: row.name for row in rows}
    return [
        DishView(
            id=row.id,
            entity_id=row.entity_id,
            name=row.name,
            description=row.description,
            world_id=row.world_id,
            origin=at(refs, row.origin_node_id),
            method=row.method,
            course=row.course,
            nourishment=row.nourishment,
            delight=row.delight,
            keeps=row.keeps,
            prestige=row.prestige,
            technique=row.technique,
            created_epoch=row.created_epoch,
            retired=row.retired,
            ingredients=[IngredientView(commodity=item.commodity, share=item.share) for item in ingredients.get(row.id, [])],
            cooked_in=[cooking_view(item, refs, names) for item in cooked.get(row.id, [])],
            locked=list(row.locked),
        )
        for row in rows
    ]


async def building_types(session: AsyncSession, rows: list[StructureDesignRow]) -> list[BuildingTypeView]:
    ids = [row.id for row in rows]
    parts = grouped(
        await session.scalars(
            select(StructureDesignSectionRow).where(StructureDesignSectionRow.design_id.in_(ids)).order_by(StructureDesignSectionRow.section)
        ),
        "design_id",
    )
    used_rows = await session.execute(
        select(StructureProfileRow.design_id, func.count()).where(StructureProfileRow.design_id.in_(ids)).group_by(StructureProfileRow.design_id)
    )
    used = {design_id: int(count) for design_id, count in used_rows if design_id is not None}
    refs = await refs_of(session, [row.origin_node_id for row in rows])
    return [
        BuildingTypeView(
            id=row.id,
            entity_id=row.entity_id,
            name=row.name,
            description=row.description,
            world_id=row.world_id,
            origin=at(refs, row.origin_node_id),
            base_kind=row.base_kind,
            kind_label=STRUCTURES[row.base_kind].label,
            form=row.form,
            storeys=row.storeys,
            material=row.material,
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
            created_epoch=row.created_epoch,
            used_by=used.get(row.id, 0),
            locked=list(row.locked),
            sections=[
                DesignSectionView(section=part.section, criticality=part.criticality, share=part.share, material=part.material)
                for part in parts.get(row.id, [])
            ],
        )
        for row in rows
    ]


@router.get("/made-kinds/world/{world_id}", response_model=WorldKindsView)
async def world_kinds(services: ServicesDep, world_id: NodeId) -> WorldKindsView:
    async with reader(services) as session:
        designs = list(
            await session.scalars(select(DesignRow).where(DesignRow.world_id == world_id).order_by(DesignRow.obsolete, DesignRow.name, DesignRow.id))
        )
        units = list(
            await session.scalars(
                select(UnitDesignRow).where(UnitDesignRow.world_id == world_id).order_by(UnitDesignRow.retired, UnitDesignRow.name, UnitDesignRow.id)
            )
        )
        models = list(
            await session.scalars(
                select(EquipmentModelRow)
                .where(EquipmentModelRow.world_id == world_id)
                .order_by(EquipmentModelRow.retired, EquipmentModelRow.name, EquipmentModelRow.id)
            )
        )
        foods = list(await session.scalars(select(DishRow).where(DishRow.world_id == world_id).order_by(DishRow.retired, DishRow.name, DishRow.id)))
        buildings = list(
            await session.scalars(
                select(StructureDesignRow)
                .where(StructureDesignRow.world_id == world_id)
                .order_by(StructureDesignRow.retired, StructureDesignRow.name, StructureDesignRow.id)
            )
        )
        return WorldKindsView(
            world_id=world_id,
            vehicle_types=await vehicle_types(session, designs),
            unit_types=await unit_types(session, units),
            equipment_models=await equipment_models(session, models),
            dishes=await dishes(session, foods),
            building_types=await building_types(session, buildings),
        )


async def group_views(session: AsyncSession, node_id: int, refs: dict[int, NodeRef]) -> list[VehicleGroupView]:
    groups = list(await session.scalars(select(VehicleGroupRow).where(VehicleGroupRow.holder_node_id == node_id).order_by(VehicleGroupRow.id)))
    sections = grouped(
        await session.scalars(
            select(VehicleGroupSectionRow).where(VehicleGroupSectionRow.group_id.in_([row.id for row in groups])).order_by(VehicleGroupSectionRow.section)
        ),
        "group_id",
    )
    regions = await refs_of(session, [row.region_entity_id for row in groups])
    found: list[VehicleGroupView] = []
    for group in groups:
        design = await session.get(DesignRow, group.design_id)
        if design is None:
            continue
        reading = await read(session, group)
        criticality = {
            part.section: part.criticality for part in await session.scalars(select(DesignSectionRow).where(DesignSectionRow.design_id == design.id))
        }
        found.append(
            VehicleGroupView(
                id=group.id,
                holder=refs[node_id],
                design_id=design.id,
                design_name=design.name,
                frame=design.frame,
                family=design.family,
                domain=design.domain,
                count=group.count,
                crewed=group.crewed,
                condition=group.condition,
                fuel=group.fuel,
                status=group.status,
                region=at(regions, group.region_entity_id),
                built_epoch=group.built_epoch,
                firepower=round(reading.firepower) if reading is not None else 0,
                armour=reading.armour if reading is not None else design.armour,
                pace=reading.pace if reading is not None else 0,
                troops=reading.troops if reading is not None else 0,
                cargo=reading.cargo if reading is not None else 0,
                crew_needed=reading.crew_needed if reading is not None else 0,
                sections=[
                    GroupSectionView(
                        section=item.section,
                        criticality=criticality.get(item.section, Criticality.MINOR),
                        damaged=item.damaged,
                        disabled=item.disabled,
                        destroyed=item.destroyed,
                        locked=list(item.locked),
                    )
                    for item in sections.get(group.id, [])
                ],
                locked=list(group.locked),
            )
        )
    return found


async def store_views(session: AsyncSession, node_id: int) -> list[StoreView]:
    rows = await session.execute(
        select(EquipmentStoreRow, EquipmentModelRow)
        .join(EquipmentModelRow, EquipmentModelRow.id == EquipmentStoreRow.model_id)
        .where(EquipmentStoreRow.holder_node_id == node_id)
        .order_by(EquipmentModelRow.slot, EquipmentModelRow.name)
    )
    return [
        StoreView(model_id=model.id, model_name=model.name, family=model.family, slot=model.slot, count=store.count, locked=list(store.locked))
        for store, model in rows
    ]


async def stack_views(session: AsyncSession, node_id: int) -> list[StackKitView]:
    stacks = list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == node_id).order_by(ArmyUnitRow.id)))
    if not stacks:
        return []
    carried = grouped(
        (
            row
            for row in await session.scalars(
                select(ArmyUnitEquipmentRow).where(ArmyUnitEquipmentRow.unit_id.in_([stack.id for stack in stacks])).order_by(ArmyUnitEquipmentRow.model_id)
            )
        ),
        "unit_id",
    )
    model_ids = sorted({row.model_id for rows in carried.values() for row in rows})
    models = {row.id: row for row in await session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.id.in_(model_ids)))} if model_ids else {}
    design_ids = [stack.design_id for stack in stacks if stack.design_id is not None]
    designs = {row.id: row.name for row in await session.scalars(select(UnitDesignRow).where(UnitDesignRow.id.in_(design_ids)))} if design_ids else {}
    return [
        StackKitView(
            unit_id=stack.id,
            kind=stack.kind,
            count=stack.count,
            design_id=stack.design_id,
            design_name=designs.get(stack.design_id) if stack.design_id is not None else None,
            carried=[
                CarriedView(
                    model_id=item.model_id,
                    model_name=models[item.model_id].name,
                    family=models[item.model_id].family,
                    slot=models[item.model_id].slot,
                    count=item.count,
                    condition=item.condition,
                    locked=list(item.locked),
                )
                for item in carried.get(stack.id, [])
                if item.model_id in models
            ],
        )
        for stack in stacks
    ]


async def vessel_views(session: AsyncSession, node_id: int) -> list[VesselSectionView]:
    vessel = await session.get(VesselProfileRow, node_id)
    if vessel is None:
        return []
    laid = {row.section: row for row in await session.scalars(select(VesselSectionRow).where(VesselSectionRow.vessel_entity_id == node_id))}
    layout = VEHICLE_LAYOUTS[FRAMES[vessel.frame].family]
    found = [
        VesselSectionView(
            section=spec.section,
            criticality=spec.criticality,
            state=laid[spec.section].state if spec.section in laid else SectionState.SOUND,
            condition=laid[spec.section].condition if spec.section in laid else PERCENT,
            laid=spec.section in laid,
            locked=list(laid[spec.section].locked) if spec.section in laid else [],
        )
        for spec in layout
    ]
    known = {spec.section for spec in layout}
    found.extend(
        VesselSectionView(section=row.section, criticality=Criticality.MINOR, state=row.state, condition=row.condition, laid=True, locked=list(row.locked))
        for row in laid.values()
        if row.section not in known
    )
    return found


async def section_views(session: AsyncSession, node_id: int) -> tuple[list[StructureSectionView], MegastructureView | None]:
    profile = await session.get(StructureProfileRow, node_id)
    if profile is None:
        return [], None
    laid = list(
        await session.scalars(select(StructureSectionRow).where(StructureSectionRow.structure_entity_id == node_id).order_by(StructureSectionRow.section))
    )
    if laid:
        sections = [
            StructureSectionView(
                section=row.section,
                role=row.role,
                criticality=row.criticality,
                share=row.share,
                exposure=row.exposure,
                hazard=row.hazard,
                neighbours=list(row.neighbours),
                condition=row.condition,
                state=row.state,
                material=row.material,
                world_material_id=row.world_material_id,
                flammability=row.flammability,
                laid=True,
                locked=list(row.locked),
            )
            for row in laid
        ]
    else:
        sections = [
            StructureSectionView(
                section=part.section,
                role=part.role,
                criticality=part.criticality,
                share=part.share,
                exposure=part.exposure,
                hazard=part.hazard,
                neighbours=list(part.neighbours),
                condition=profile.condition,
                state=SectionState.SOUND,
                material=None,
                world_material_id=None,
                flammability=0,
                laid=False,
                locked=[],
            )
            for part in STRUCTURE_LAYOUTS[profile.kind]
        ]
    mega = await session.get(MegastructureRow, node_id) if profile.kind in MEGASTRUCTURES else None
    megastructure = (
        MegastructureView(kind=profile.kind, target_orbit=mega.target_orbit, output=mega.output, updated_epoch=mega.updated_epoch, locked=list(mega.locked))
        if mega is not None
        else (MegastructureView(kind=profile.kind, target_orbit=None, output=0, updated_epoch=0, locked=[]) if profile.kind in MEGASTRUCTURES else None)
    )
    return sections, megastructure


async def attraction_view(session: AsyncSession, node_id: int) -> AttractionView | None:
    profile = await session.get(MortalProfileRow, node_id)
    if profile is None:
        return None
    drawn = [MortalSex(value) for value in profile.drawn_to] if profile.drawn_to is not None else None
    return AttractionView(
        drawn_to=drawn,
        attraction=profile.attraction,
        decline=await decline_severity(session, node_id),
        held=[key for key in profile.locked if key in {"drawn_to", "attraction"}],
    )


HEALED = (InjuryState.HEALED_SCAR,)


async def being_view(session: AsyncSession, rules: Rules, entity: EntityRow | None) -> BeingWoundsView | None:
    if entity is None or entity.entity_type not in VAST:
        return None
    body = await session.get(BodyRow, entity.id)
    profile = await session.get(CosmicBeingProfileRow, entity.id)
    table = rules.cosmic_wounds
    open_wounds = await session.scalar(select(func.count()).select_from(InjuryRow).where(InjuryRow.bearer_node_id == entity.id, InjuryRow.state.not_in(HEALED)))
    return BeingWoundsView(
        grown=body is not None,
        hp=stat(entity, "hp"),
        hp_max=body.hp_max if body is not None else None,
        might=profile.might if profile is not None else None,
        effective_might=await effective_might(session, entity, profile.might) if profile is not None else None,
        vital=body.vital if body is not None else None,
        mobility=body.mobility if body is not None else None,
        sight=body.sight if body is not None else None,
        roams=await can_roam(session, table.roam_floor, entity),
        sees=await can_see(session, table.sight_floor, entity),
        wounds=int(open_wounds or 0),
        held=held(entity.id),
    )


async def own_kinds(session: AsyncSession, node_id: int) -> OwnKindsView:
    vehicles = await session.scalars(select(DesignRow).where(DesignRow.origin_node_id == node_id).order_by(DesignRow.name))
    units = await session.scalars(select(UnitDesignRow).where(UnitDesignRow.origin_node_id == node_id).order_by(UnitDesignRow.name))
    models = await session.scalars(select(EquipmentModelRow).where(EquipmentModelRow.origin_node_id == node_id).order_by(EquipmentModelRow.name))
    foods = await session.scalars(select(DishRow).where(DishRow.origin_node_id == node_id).order_by(DishRow.name))
    buildings = await session.scalars(select(StructureDesignRow).where(StructureDesignRow.origin_node_id == node_id).order_by(StructureDesignRow.name))
    return OwnKindsView(
        vehicle_types=[
            KindRef(id=row.id, entity_id=row.entity_id, name=row.name, family=FRAMES[row.frame].label if row.frame is not None else row.kind.value)
            for row in vehicles
        ],
        unit_types=[KindRef(id=row.id, entity_id=row.entity_id, name=row.name, family=UNITS[row.base_kind].label) for row in units],
        equipment_models=[KindRef(id=row.id, entity_id=row.entity_id, name=row.name, family=FAMILIES[row.family].label) for row in models],
        dishes=[KindRef(id=row.id, entity_id=row.entity_id, name=row.name, family=row.course.value.replace("_", " ")) for row in foods],
        building_types=[KindRef(id=row.id, entity_id=row.entity_id, name=row.name, family=STRUCTURES[row.base_kind].label) for row in buildings],
    )


@router.get("/made-kinds/thing/{node_id}", response_model=ThingKindsView)
async def thing_kinds(services: ServicesDep, node_id: NodeId) -> ThingKindsView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such thing.")
        refs = await refs_of(session, [node_id])
        entity = await session.get(EntityRow, node_id)
        cooking_rows = list(
            await session.scalars(select(CommunityDishRow).where(CommunityDishRow.community_entity_id == node_id).order_by(CommunityDishRow.popularity.desc()))
        )
        names = (
            {row.id: row.name for row in await session.scalars(select(DishRow).where(DishRow.id.in_([row.dish_id for row in cooking_rows])))}
            if cooking_rows
            else {}
        )
        sections, megastructure = await section_views(session, node_id)
        rules = services.rules.current
        return ThingKindsView(
            node=refs[node_id],
            world_id=entity.world_id if entity is not None else None,
            vehicle_groups=await group_views(session, node_id, refs),
            stores=await store_views(session, node_id),
            stacks=await stack_views(session, node_id),
            pace=await army_pace(session, node_id),
            vessel_sections=await vessel_views(session, node_id),
            cooking=[cooking_view(row, refs, names) for row in cooking_rows],
            sections=sections,
            megastructure=megastructure,
            attraction=await attraction_view(session, node_id),
            being=await being_view(session, rules, entity),
            own=await own_kinds(session, node_id),
        )
