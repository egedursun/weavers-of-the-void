from pydantic import Field

from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.kinds import IngredientRole
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.structure import StructureSection
from aerona.domain.enums.vehicles import MountKind, VehicleSection
from aerona.engine.cosmos.being_wounds import FORCE_MAX, strike
from aerona.engine.cuisine import control as cuisine
from aerona.engine.equipment import control as equipment
from aerona.engine.lifecycle.wounds import WoundOutcome
from aerona.engine.mortal.attraction import set_attraction
from aerona.engine.structures import control as structures
from aerona.engine.vehicles import control as vehicles
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
NAME = 200
LOTS = 1_000_000


class SectionDraft(Edited):
    design_id: int
    section: VehicleSection


class SectionTarget(Command):
    design_id: int
    section: VehicleSection


class MountDraft(Edited):
    design_id: int
    mount: MountKind


class RecordTarget(Command):
    record_id: int


class RecordEdit(Edited):
    record_id: int


class TechniqueDraft(Command):
    design_id: int
    technique: Technique


class GroupDraft(Command):
    holder_id: int
    design_id: int
    count: int = Field(default=1, ge=1, le=LOTS)
    crewed: int = Field(default=0, ge=0, le=LOTS)
    region_id: int | None = None


class GroupMove(Command):
    group_id: int
    holder_id: int
    count: int = Field(default=1, ge=1, le=LOTS)


class GroupRepair(Command):
    group_id: int
    points: int = Field(default=SPAN, ge=1, le=LOTS)


class GroupSectionDraft(Edited):
    group_id: int
    section: VehicleSection


class GroupSectionTarget(Command):
    group_id: int
    section: VehicleSection


class VesselSectionDraft(Edited):
    vessel_id: int
    section: VehicleSection


class VesselSectionTarget(Command):
    vessel_id: int
    section: VehicleSection


class ModelDraft(Command):
    origin_id: int | None = None
    world_id: int | None = None
    family: EquipmentFamily
    name: str | None = Field(default=None, max_length=NAME)
    quality: int = Field(default=50, ge=0, le=SPAN)


class StoreDraft(Command):
    holder_id: int
    model_id: int
    count: int = Field(default=0, ge=0, le=LOTS)


class StoreTarget(Command):
    holder_id: int
    model_id: int


class CarriedDraft(Command):
    unit_id: int
    model_id: int
    count: int = Field(default=0, ge=0, le=LOTS)
    condition: int = Field(default=SPAN, ge=0, le=SPAN)


class CarriedTarget(Command):
    unit_id: int
    model_id: int


class UnitTypeDraft(Command):
    owner_id: int
    role: UnitKind
    name: str | None = Field(default=None, max_length=NAME)


class LoadoutDraft(Command):
    design_id: int
    model_id: int
    count: int = Field(default=1, ge=1, le=10)


class LoadoutTarget(Command):
    design_id: int
    model_id: int


class UnitTechniqueDraft(Command):
    design_id: int
    technique: Technique


class StructureSectionDraft(Edited):
    structure_id: int
    section: StructureSection


class StructureSectionTarget(Command):
    structure_id: int
    section: StructureSection


STRUCK = {
    WoundOutcome.IMMORTAL: "The blow lands, but nothing can kill it.",
    WoundOutcome.WOUNDED: "The blow lands and the being is wounded.",
    WoundOutcome.DIED: "The blow lands and the being falls.",
}


class BeingStrike(Command):
    being_id: int
    force: int = Field(default=1, ge=1, le=FORCE_MAX)
    reason: str = Field(default="struck by the Creator", min_length=1, max_length=200)


class StructureStrike(Command):
    structure_id: int
    section: StructureSection
    damage: int = Field(default=40, ge=1, le=SPAN)


class DesignSectionDraft(Edited):
    design_id: int
    section: StructureSection


class DesignSectionTarget(Command):
    design_id: int
    section: StructureSection


class MegastructureEdit(Edited):
    structure_id: int


class StructureTarget(Command):
    structure_id: int


class DishDraft(Command):
    origin_id: int | None = None
    world_id: int | None = None
    method: CookingMethod
    course: DishCourse = DishCourse.STAPLE
    name: str | None = Field(default=None, max_length=NAME)
    ingredients: list[CommodityKind] = Field(default_factory=list)


class IngredientDraft(Command):
    dish_id: int
    commodity: CommodityKind
    share: int = Field(default=50, ge=1, le=SPAN)
    role: IngredientRole = IngredientRole.BASE
    good_kind_id: int | None = None


class IngredientTarget(Command):
    dish_id: int
    commodity: CommodityKind


class StepDraft(Command):
    dish_id: int
    step: int = Field(default=1, ge=1, le=SPAN)
    method: CookingMethod
    duration: int = Field(default=1, ge=0, le=1000)


class CookingDraft(Command):
    community_id: int
    dish_id: int
    popularity: int = Field(default=50, ge=0, le=SPAN)


class CookingTarget(Command):
    community_id: int
    dish_id: int


class CookingEdit(Edited):
    community_id: int
    dish_id: int


class AttractionDraft(Command):
    mortal_id: int
    drawn_to: list[SexKind] | None = None
    attraction: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


@player_action("mortal:attraction", ActionKind.EDIT_RECORD)
async def mortal_attraction(scope: PlayerScope, command: AttractionDraft) -> Effect:
    await set_attraction(await scope.context("mortal_attraction"), command.mortal_id, command.drawn_to, command.attraction, hold=command.hold)
    return Effect("Whom this mortal is drawn to is set so.", command.mortal_id)


@player_action("design_section:set", ActionKind.EDIT_RECORD)
async def design_section_set(scope: PlayerScope, command: SectionDraft) -> Effect:
    await vehicles.set_section(await scope.context("design_section_set"), command.design_id, command.section, command.values)
    return Effect("The section of the vehicle type is set so.")


@player_action("design_section:delete", ActionKind.EDIT_RECORD)
async def design_section_delete(scope: PlayerScope, command: SectionTarget) -> Effect:
    await vehicles.remove_section(await scope.context("design_section_delete"), command.design_id, command.section)
    return Effect("The section is taken out of the vehicle type.")


@player_action("design_mount:add", ActionKind.EDIT_RECORD)
async def design_mount_add(scope: PlayerScope, command: MountDraft) -> Effect:
    row = await vehicles.add_mount(await scope.context("design_mount_add"), command.design_id, command.mount, command.values)
    return Effect("A weapon mount is added.", created_ids=(row.id,))


@player_action("design_mount:edit", ActionKind.EDIT_RECORD)
async def design_mount_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await vehicles.edit_record(await scope.context("design_mount_edit"), "design_mount", command.record_id, command.values, command.release)
    return Effect("The weapon mount is set so.")


@player_action("design_mount:delete", ActionKind.EDIT_RECORD)
async def design_mount_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await vehicles.remove_mount(await scope.context("design_mount_delete"), command.record_id)
    return Effect("The weapon mount is taken off.")


@player_action("design_technique:add", ActionKind.EDIT_RECORD)
async def design_technique_add(scope: PlayerScope, command: TechniqueDraft) -> Effect:
    await vehicles.add_technique(await scope.context("design_technique_add"), command.design_id, command.technique)
    return Effect("The vehicle type now needs this technique.")


@player_action("design_technique:delete", ActionKind.EDIT_RECORD)
async def design_technique_delete(scope: PlayerScope, command: TechniqueDraft) -> Effect:
    await vehicles.remove_technique(await scope.context("design_technique_delete"), command.design_id, command.technique)
    return Effect("The vehicle type no longer needs this technique.")


@player_action("vehicle_group:create", ActionKind.EDIT_RECORD)
async def vehicle_group_create(scope: PlayerScope, command: GroupDraft) -> Effect:
    row = await vehicles.new_group(
        await scope.context("vehicle_group_create"), command.holder_id, command.design_id, command.count, crewed=command.crewed, region_id=command.region_id
    )
    return Effect("The vehicles are given.", command.holder_id, created_ids=(row.id,))


@player_action("vehicle_group:edit", ActionKind.EDIT_RECORD)
async def vehicle_group_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await vehicles.edit_record(await scope.context("vehicle_group_edit"), "vehicle_group", command.record_id, command.values, command.release)
    return Effect("The vehicle group is set so.")


@player_action("vehicle_group:move", ActionKind.EDIT_RECORD)
async def vehicle_group_move(scope: PlayerScope, command: GroupMove) -> Effect:
    moved = await vehicles.move_group(await scope.context("vehicle_group_move"), command.group_id, command.holder_id, command.count)
    return Effect(f"{several(moved, 'vehicle', 'vehicles')} change hands.", command.holder_id)


@player_action("vehicle_group:repair", ActionKind.EDIT_RECORD)
async def vehicle_group_repair(scope: PlayerScope, command: GroupRepair) -> Effect:
    await vehicles.repair(await scope.context("vehicle_group_repair"), command.group_id, command.points)
    return Effect("The vehicles are mended.")


@player_action("vehicle_group:delete", ActionKind.EDIT_RECORD)
async def vehicle_group_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await vehicles.delete_record(await scope.context("vehicle_group_delete"), "vehicle_group", command.record_id)
    return Effect("The vehicle group is gone.")


@player_action("vehicle_group_section:set", ActionKind.EDIT_RECORD)
async def vehicle_group_section_set(scope: PlayerScope, command: GroupSectionDraft) -> Effect:
    await vehicles.set_group_section(await scope.context("vehicle_group_section_set"), command.group_id, command.section, command.values)
    return Effect("The damage of the group is set so.")


@player_action("vehicle_group_section:delete", ActionKind.EDIT_RECORD)
async def vehicle_group_section_delete(scope: PlayerScope, command: GroupSectionTarget) -> Effect:
    await vehicles.clear_group_section(await scope.context("vehicle_group_section_delete"), command.group_id, command.section)
    return Effect("That section of the group is whole again.")


@player_action("vessel_section:set", ActionKind.EDIT_RECORD)
async def vessel_section_set(scope: PlayerScope, command: VesselSectionDraft) -> Effect:
    await vehicles.set_vessel_section(await scope.context("vessel_section_set"), command.vessel_id, command.section, command.values)
    return Effect("The section of the vessel is set so.", command.vessel_id)


@player_action("vessel_section:delete", ActionKind.EDIT_RECORD)
async def vessel_section_delete(scope: PlayerScope, command: VesselSectionTarget) -> Effect:
    await vehicles.delete_record(await scope.context("vessel_section_delete"), "vessel_section", (command.vessel_id, command.section))
    return Effect("That section of the vessel is whole again.", command.vessel_id)


@player_action("equipment_model:create", ActionKind.EDIT_RECORD)
async def equipment_model_create(scope: PlayerScope, command: ModelDraft) -> Effect:
    row = await equipment.new_model(
        await scope.context("equipment_model_create"), command.origin_id, command.family, world_id=command.world_id, name=command.name, quality=command.quality
    )
    return Effect(f"{row.name} is made.", command.origin_id, created_ids=(row.id,))


@player_action("equipment_model:edit", ActionKind.EDIT_RECORD)
async def equipment_model_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await equipment.edit_record(await scope.context("equipment_model_edit"), "equipment_model", command.record_id, command.values, command.release)
    return Effect("The model is set so.")


@player_action("equipment_model:delete", ActionKind.EDIT_RECORD)
async def equipment_model_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await equipment.delete_record(await scope.context("equipment_model_delete"), "equipment_model", command.record_id)
    return Effect("The model is forgotten.")


@player_action("equipment_store:set", ActionKind.EDIT_RECORD)
async def equipment_store_set(scope: PlayerScope, command: StoreDraft) -> Effect:
    await equipment.set_store(await scope.context("equipment_store_set"), command.holder_id, command.model_id, command.count)
    return Effect("The store is set so.", command.holder_id)


@player_action("equipment_store:delete", ActionKind.EDIT_RECORD)
async def equipment_store_delete(scope: PlayerScope, command: StoreTarget) -> Effect:
    await equipment.delete_record(await scope.context("equipment_store_delete"), "equipment_store", (command.holder_id, command.model_id))
    return Effect("The store is emptied.", command.holder_id)


@player_action("army_equipment:set", ActionKind.EDIT_RECORD)
async def army_equipment_set(scope: PlayerScope, command: CarriedDraft) -> Effect:
    await equipment.set_carried(await scope.context("army_equipment_set"), command.unit_id, command.model_id, command.count, command.condition)
    return Effect("The stack carries it so.")


@player_action("army_equipment:delete", ActionKind.EDIT_RECORD)
async def army_equipment_delete(scope: PlayerScope, command: CarriedTarget) -> Effect:
    await equipment.drop_carried(await scope.context("army_equipment_delete"), command.unit_id, command.model_id)
    return Effect("The stack no longer carries it.")


@player_action("unit_type:create", ActionKind.EDIT_RECORD)
async def unit_type_create(scope: PlayerScope, command: UnitTypeDraft) -> Effect:
    row = await equipment.new_unit_type(await scope.context("unit_type_create"), command.owner_id, command.role, command.name)
    return Effect(f"{row.name} take the field.", command.owner_id, created_ids=(row.id,))


@player_action("unit_type:edit", ActionKind.EDIT_RECORD)
async def unit_type_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await equipment.edit_record(await scope.context("unit_type_edit"), "unit_type", command.record_id, command.values, command.release)
    return Effect("The kind of soldier is set so.")


@player_action("unit_type:delete", ActionKind.EDIT_RECORD)
async def unit_type_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await equipment.delete_record(await scope.context("unit_type_delete"), "unit_type", command.record_id)
    return Effect("The kind of soldier is struck.")


@player_action("unit_loadout:set", ActionKind.EDIT_RECORD)
async def unit_loadout_set(scope: PlayerScope, command: LoadoutDraft) -> Effect:
    await equipment.set_loadout(await scope.context("unit_loadout_set"), command.design_id, command.model_id, command.count)
    return Effect("The loadout is set so.")


@player_action("unit_loadout:delete", ActionKind.EDIT_RECORD)
async def unit_loadout_delete(scope: PlayerScope, command: LoadoutTarget) -> Effect:
    await equipment.remove_loadout(await scope.context("unit_loadout_delete"), command.design_id, command.model_id)
    return Effect("The piece is taken from the loadout.")


@player_action("unit_technique:add", ActionKind.EDIT_RECORD)
async def unit_technique_add(scope: PlayerScope, command: UnitTechniqueDraft) -> Effect:
    await equipment.add_unit_technique(await scope.context("unit_technique_add"), command.design_id, command.technique)
    return Effect("The kind of soldier now needs this technique.")


@player_action("unit_technique:delete", ActionKind.EDIT_RECORD)
async def unit_technique_delete(scope: PlayerScope, command: UnitTechniqueDraft) -> Effect:
    await equipment.remove_unit_technique(await scope.context("unit_technique_delete"), command.design_id, command.technique)
    return Effect("The kind of soldier no longer needs this technique.")


@player_action("structure_section:edit", ActionKind.EDIT_RECORD)
async def structure_section_edit(scope: PlayerScope, command: StructureSectionDraft) -> Effect:
    await structures.edit_section(await scope.context("structure_section_edit"), command.structure_id, command.section, command.values, command.release)
    return Effect("The section is set so.", command.structure_id)


@player_action("structure_section:repair", ActionKind.EDIT_RECORD)
async def structure_section_repair(scope: PlayerScope, command: StructureSectionTarget) -> Effect:
    await structures.repair_section(await scope.context("structure_section_repair"), command.structure_id, command.section)
    return Effect("The section is whole again.", command.structure_id)


@player_action("structure_section:strike", ActionKind.EDIT_RECORD)
async def structure_section_strike(scope: PlayerScope, command: StructureStrike) -> Effect:
    await structures.strike_section(await scope.context("structure_section_strike"), command.structure_id, command.section, command.damage)
    return Effect("The section is struck.", command.structure_id)


@player_action("cosmic_wound:strike", ActionKind.EDIT_RECORD)
async def cosmic_wound_strike(scope: PlayerScope, command: BeingStrike) -> Effect:
    outcome = await strike(await scope.context("cosmic_wound_strike"), command.being_id, command.force, command.reason)
    return Effect(STRUCK[outcome], command.being_id)


@player_action("structure_section:delete", ActionKind.EDIT_RECORD)
async def structure_section_delete(scope: PlayerScope, command: StructureSectionTarget) -> Effect:
    await structures.remove_section(await scope.context("structure_section_delete"), command.structure_id, command.section)
    return Effect("The section is taken away.", command.structure_id)


@player_action("structure_design_section:set", ActionKind.EDIT_RECORD)
async def structure_design_section_set(scope: PlayerScope, command: DesignSectionDraft) -> Effect:
    await structures.set_design_section(await scope.context("structure_design_section_set"), command.design_id, command.section, command.values)
    return Effect("The design's section is set so.")


@player_action("structure_design_section:delete", ActionKind.EDIT_RECORD)
async def structure_design_section_delete(scope: PlayerScope, command: DesignSectionTarget) -> Effect:
    await structures.remove_design_section(await scope.context("structure_design_section_delete"), command.design_id, command.section)
    return Effect("The design follows its kind's layout there again.")


@player_action("megastructure:edit", ActionKind.EDIT_RECORD)
async def megastructure_edit(scope: PlayerScope, command: MegastructureEdit) -> Effect:
    await structures.set_megastructure(await scope.context("megastructure_edit"), command.structure_id, command.values, command.release)
    return Effect("The megastructure is set so.", command.structure_id)


@player_action("megastructure:delete", ActionKind.EDIT_RECORD)
async def megastructure_delete(scope: PlayerScope, command: StructureTarget) -> Effect:
    await structures.clear_megastructure(await scope.context("megastructure_delete"), command.structure_id)
    return Effect("The megastructure starts afresh.", command.structure_id)


@player_action("dish:create", ActionKind.EDIT_RECORD)
async def dish_create(scope: PlayerScope, command: DishDraft) -> Effect:
    row = await cuisine.new_dish(
        await scope.context("dish_create"),
        command.origin_id,
        command.method,
        command.course,
        world_id=command.world_id,
        name=command.name,
        ingredients=command.ingredients,
    )
    return Effect(f"{row.name} is cooked for the first time.", command.origin_id, created_ids=(row.id,))


@player_action("dish:edit", ActionKind.EDIT_RECORD)
async def dish_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await cuisine.edit_record(await scope.context("dish_edit"), "dish", command.record_id, command.values, command.release)
    return Effect("The dish is set so.")


@player_action("dish:delete", ActionKind.EDIT_RECORD)
async def dish_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await cuisine.delete_record(await scope.context("dish_delete"), "dish", command.record_id)
    return Effect("The dish is forgotten.")


@player_action("dish_ingredient:set", ActionKind.EDIT_RECORD)
async def dish_ingredient_set(scope: PlayerScope, command: IngredientDraft) -> Effect:
    ctx = await scope.context("dish_ingredient_set")
    await cuisine.set_ingredient(ctx, command.dish_id, command.commodity, command.share, role=command.role, good_kind_id=command.good_kind_id)
    return Effect("The ingredient is set so.")


@player_action("dish_ingredient:delete", ActionKind.EDIT_RECORD)
async def dish_ingredient_delete(scope: PlayerScope, command: IngredientTarget) -> Effect:
    await cuisine.remove_ingredient(await scope.context("dish_ingredient_delete"), command.dish_id, command.commodity)
    return Effect("The ingredient is left out.")


@player_action("dish_step:set", ActionKind.EDIT_RECORD)
async def dish_step_set(scope: PlayerScope, command: StepDraft) -> Effect:
    row = await cuisine.set_step(await scope.context("dish_step_set"), command.dish_id, command.step, command.method, command.duration)
    return Effect(f"Step {row.step} of the dish is set so.", created_ids=(row.id,))


@player_action("dish_step:edit", ActionKind.EDIT_RECORD)
async def dish_step_edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    await cuisine.edit_record(await scope.context("dish_step_edit"), "dish_step", command.record_id, command.values, command.release)
    return Effect("The step is set so.")


@player_action("dish_step:delete", ActionKind.EDIT_RECORD)
async def dish_step_delete(scope: PlayerScope, command: RecordTarget) -> Effect:
    await cuisine.remove_step(await scope.context("dish_step_delete"), command.record_id)
    return Effect("The step is taken out of the dish.")


@player_action("community_dish:set", ActionKind.EDIT_RECORD)
async def community_dish_set(scope: PlayerScope, command: CookingDraft) -> Effect:
    await cuisine.cook_in(await scope.context("community_dish_set"), command.community_id, command.dish_id, command.popularity)
    return Effect("The community cooks it.", command.community_id)


@player_action("community_dish:edit", ActionKind.EDIT_RECORD)
async def community_dish_edit(scope: PlayerScope, command: CookingEdit) -> Effect:
    key = (command.community_id, command.dish_id)
    await cuisine.edit_record(await scope.context("community_dish_edit"), "community_dish", key, command.values, command.release)
    return Effect("The dish is cooked so.", command.community_id)


@player_action("community_dish:delete", ActionKind.EDIT_RECORD)
async def community_dish_delete(scope: PlayerScope, command: CookingTarget) -> Effect:
    await cuisine.delete_record(await scope.context("community_dish_delete"), "community_dish", (command.community_id, command.dish_id))
    return Effect("The community no longer cooks it.", command.community_id)
