from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.cuisine import DISH_FOODS
from aerona.catalog.equipment import FAMILIES
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.vehicles import FRAMES
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN, SHORT_DESCRIPTION_MAX
from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import BuildingForm, StructureKind
from aerona.domain.enums.vehicles import MountKind, VehicleFrame
from aerona.engine.collective.designs import FULL_SIZE, draw_design, frame_sizes
from aerona.engine.cosmos.being_wounds import FORCE_MAX, VAST, wound_being
from aerona.engine.cuisine.dishes import found_dish
from aerona.engine.equipment.models import draw_model
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.structures.types import draw_structure_type
from aerona.engine.vehicles.control import add_mount
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, label_of, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Description = Annotated[str, Field(max_length=SHORT_DESCRIPTION_MAX)]
Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
MOUNTS_MAX = 8
INGREDIENTS_MAX = 4
EMPHASIS = 2


class ShapeVehicleTypeInput(ToolInput):
    owner_id: int
    frame: VehicleFrame
    name: Name | None = None
    emphasis: DesignComponentKind | None = None
    mounts: list[MountKind] = Field(default_factory=list, max_length=MOUNTS_MAX)
    description: Description | None = None


class ShapeEquipmentInput(ToolInput):
    owner_id: int
    family: EquipmentFamily
    name: Name | None = None
    material: MaterialKind | None = None
    quality: Annotated[int, Field(ge=0, le=PERCENT)] = PERCENT // 2
    description: Description | None = None


class ShapeDishInput(ToolInput):
    owner_id: int
    method: CookingMethod
    course: DishCourse
    ingredients: list[CommodityKind] = Field(min_length=1, max_length=INGREDIENTS_MAX)
    name: Name | None = None
    description: Description | None = None


class ShapeStructureTypeInput(ToolInput):
    owner_id: int
    structure_kind: StructureKind
    form: BuildingForm | None = None
    storeys: Annotated[int, Field(ge=1, le=200)] | None = None
    material: MaterialKind | None = None
    name: Name | None = None
    description: Description | None = None


class StrikeBeingInput(ToolInput):
    being_id: int
    force: Annotated[int, Field(ge=1, le=FORCE_MAX)] = 1
    reason: Reason


async def maker(call: SonCall, owner_id: int) -> EntityRow:
    owner = await require_canon(call.session, owner_id)
    if owner.entity_type not in COMMUNITY_TYPES:
        fail(SonResult.SHAPING_TARGET, id=owner.id, name=owner.name)
    await ensure_in_reach(call, owner)
    return owner


def pay(call: SonCall, cost: int, target: int) -> None:
    call.spend_essence(cost)
    call.target(target)


async def shape_vehicle_type(call: SonCall, args: ShapeVehicleTypeInput) -> str:
    owner = await maker(call, args.owner_id)
    cost = call.rules.vehicles.son_type_essence
    require_essence(call, cost)
    sizes = frame_sizes(args.frame)
    if args.emphasis is not None:
        if args.emphasis not in sizes:
            fail(SonResult.SHAPING_REFUSED, reason=f"{an(FRAMES[args.frame].label.lower())} has no {args.emphasis.value.replace('_', ' ')}")
        sizes[args.emphasis] = min(FULL_SIZE, sizes[args.emphasis] + EMPHASIS)
    design = await draw_design(call.tick, owner, args.frame, sizes=sizes, name=args.name, knowledge=await KnowledgeMap.load(call.session))
    design.description = args.description
    for mount in args.mounts:
        await add_mount(call.tick, design.id, mount, {})
    pay(call, cost, owner.id)
    frame = FRAMES[args.frame].label.lower()
    await call.chronicle(ChronicleKind.WAR, lines.SHAPE_VEHICLE_TYPE, entity_ids=[owner.id], son=call.son.name, owner=owner.name, name=design.name)
    return result(
        SonResult.VEHICLE_TYPE_SHAPED,
        owner=owner.name,
        name=design.name,
        id=design.id,
        frame=frame,
        speed=design.speed,
        arms=design.armament,
        crew=design.crew,
        cargo=design.cargo,
    )


async def shape_equipment(call: SonCall, args: ShapeEquipmentInput) -> str:
    owner = await maker(call, args.owner_id)
    cost = call.rules.armament.son_model_essence
    require_essence(call, cost)
    model = await draw_model(call.tick, owner, args.family, world_id=owner.world_id, quality=args.quality, material=args.material, name=args.name)
    model.description = args.description
    pay(call, cost, owner.id)
    family = FAMILIES[args.family].label.lower()
    await call.chronicle(ChronicleKind.WORLD, lines.SHAPE_EQUIPMENT, entity_ids=[owner.id], son=call.son.name, owner=owner.name, name=model.name)
    return result(SonResult.EQUIPMENT_SHAPED, owner=owner.name, name=model.name, id=model.id, family=family, quality=model.quality)


async def shape_dish(call: SonCall, args: ShapeDishInput) -> str:
    owner = await maker(call, args.owner_id)
    cost = call.rules.cuisine.son_dish_essence
    require_essence(call, cost)
    foods = list(dict.fromkeys(food for food in args.ingredients if food in DISH_FOODS))
    if not foods:
        fail(SonResult.SHAPING_REFUSED, reason="none of those is food: " + ", ".join(food.value for food in DISH_FOODS))
    dish = await found_dish(call.tick, owner, args.method, args.course, foods, world_id=owner.world_id, name=args.name)
    dish.description = args.description
    pay(call, cost, owner.id)
    await call.chronicle(ChronicleKind.CULTURE, lines.SHAPE_DISH, entity_ids=[owner.id], son=call.son.name, owner=owner.name, name=dish.name)
    return result(SonResult.DISH_SHAPED, owner=owner.name, name=dish.name, id=dish.id, method=args.method.value, course=label_of(args.course))


async def shape_structure_type(call: SonCall, args: ShapeStructureTypeInput) -> str:
    owner = await maker(call, args.owner_id)
    cost = call.rules.integrity.son_type_essence
    require_essence(call, cost)
    design = await draw_structure_type(
        call.tick,
        owner,
        args.structure_kind,
        world_id=owner.world_id,
        name=args.name,
        form=args.form,
        storeys=args.storeys,
        material=args.material,
        son_id=call.son.id,
    )
    design.description = args.description
    pay(call, cost, owner.id)
    kind = STRUCTURES[args.structure_kind].label.lower()
    await call.chronicle(ChronicleKind.WORLD, lines.SHAPE_STRUCTURE_TYPE, entity_ids=[owner.id], son=call.son.name, owner=owner.name, name=design.name)
    return result(SonResult.STRUCTURE_TYPE_SHAPED, owner=owner.name, name=design.name, id=design.id, kind=kind)


async def strike_being(call: SonCall, args: StrikeBeingInput) -> str:
    being = await require_canon(call.session, args.being_id)
    if being.entity_type not in VAST:
        fail(SonResult.NOT_A_VAST_BEING, id=being.id, name=being.name)
    await ensure_in_reach(call, being)
    table = call.rules.cosmic_wounds
    cost = table.strike_essence * args.force
    require_essence(call, cost)
    outcome = await wound_being(call.tick, being, table.strike_harm * args.force, HarmCause.GOD, args.reason, killer_id=call.son.id)
    if outcome is None:
        fail(SonResult.SHAPING_REFUSED, reason=f"{being.name} cannot be struck now")
    pay(call, cost, being.id)
    await call.chronicle(ChronicleKind.MIRACLE, lines.STRIKE_BEING, entity_ids=[being.id], son=call.son.name, being=being.name, reason=args.reason)
    return result(SonResult.BEING_STRUCK, name=being.name, outcome=label_of(outcome))


def essence(field: str, namespace: str) -> Any:
    return lambda rules: getattr(getattr(rules, namespace), field)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    standard = son_standard_action
    return [
        ToolSpec(
            SonToolId.SHAPE_VEHICLE_TYPE,
            son,
            ShapeVehicleTypeInput,
            ToolMeta(ActionKind.BUILD_SHIP, standard, essence_cost=essence("son_type_essence", "vehicles")),
            shape_vehicle_type,
        ),
        ToolSpec(
            SonToolId.SHAPE_EQUIPMENT,
            son,
            ShapeEquipmentInput,
            ToolMeta(ActionKind.PRODUCE, standard, essence_cost=essence("son_model_essence", "armament")),
            shape_equipment,
        ),
        ToolSpec(
            SonToolId.SHAPE_DISH,
            son,
            ShapeDishInput,
            ToolMeta(ActionKind.CREATE_CULTURE, standard, essence_cost=essence("son_dish_essence", "cuisine")),
            shape_dish,
        ),
        ToolSpec(
            SonToolId.SHAPE_STRUCTURE_TYPE,
            son,
            ShapeStructureTypeInput,
            ToolMeta(ActionKind.BUILD, standard, essence_cost=essence("son_type_essence", "integrity")),
            shape_structure_type,
        ),
        ToolSpec(
            SonToolId.STRIKE_BEING,
            son,
            StrikeBeingInput,
            ToolMeta(ActionKind.WRATH, standard, essence_cost=lambda rules: rules.cosmic_wounds.strike_essence),
            strike_being,
        ),
    ]
