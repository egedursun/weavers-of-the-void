from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.cuisine import DISH_FOODS
from aerona.catalog.equipment import FAMILIES
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.units import UNITS
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, SHORT_DESCRIPTION_MAX
from aerona.constants.units import PERCENT
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import BuildingForm, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.cuisine.dishes import found_dish, known_methods
from aerona.engine.equipment.models import draw_model, known
from aerona.engine.military.unit_types import draw_type
from aerona.engine.mind.book import best_skill
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.structures.types import draw_structure_type
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.collective import design_owner
from aerona.tools.mortal.support import craft_of

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Description = Annotated[str, Field(max_length=SHORT_DESCRIPTION_MAX)]
INGREDIENTS_MAX = 4
COMMAND_SKILLS = (SkillKind.TACTICS, SkillKind.STRATEGY)
FORGE_SKILLS = (SkillKind.SMITHING, SkillKind.ENGINEERING)
BUILD_SKILLS = (SkillKind.ENGINEERING,)


class DraftUnitTypeInput(ToolInput):
    role: UnitKind
    name: Name | None = None
    description: Description | None = None


class ForgeModelInput(ToolInput):
    family: EquipmentFamily
    name: Name | None = None
    description: Description | None = None


class CreateDishInput(ToolInput):
    method: CookingMethod
    course: DishCourse
    ingredients: list[CommodityKind] = Field(min_length=1, max_length=INGREDIENTS_MAX)
    name: Name | None = None
    description: Description | None = None


class DrawStructureTypeInput(ToolInput):
    structure_kind: StructureKind
    form: BuildingForm | None = None
    storeys: Annotated[int, Field(ge=1, le=200)] | None = None
    name: Name | None = None
    description: Description | None = None


async def maker(call: MortalCall, refused: MortalResult) -> EntityRow:
    owner = await design_owner(call)
    if owner is None or held(owner.id):
        fail(refused, why="you make things for no town or realm")
    return owner


async def own_people(call: MortalCall, refused: MortalResult) -> EntityRow:
    people = await people_of(call.session, call.me)
    if people is not None and not held(people.id):
        return people
    return await maker(call, refused)


def skilled(level: int, craft: int) -> int:
    return max(1, min(PERCENT, (level + craft) // 2))


async def draft_unit_type(call: MortalCall, args: DraftUnitTypeInput) -> str:
    owner = await maker(call, MortalResult.UNIT_TYPE_REFUSED)
    if await best_skill(call.session, call.me.id, COMMAND_SKILLS) < call.rules.unit_types.draft_skill:
        fail(MortalResult.UNIT_TYPE_REFUSED, why="you know too little of war to set out a new kind of soldier")
    design = await draw_type(call.tick, owner, args.role, await KnowledgeMap.load(call.session), name=args.name)
    design.description = args.description
    call.target(owner.id)
    roles = {IncidentRole.ACTOR: call.me.id, IncidentRole.OWNER: owner.id, **({IncidentRole.PRODUCT: design.entity_id} if design.entity_id is not None else {})}
    await call.record("tools.mortal.draft_unit_type", roles=roles)
    return result(
        MortalResult.UNIT_TYPE_DRAFTED,
        owner=owner.name,
        name=design.name,
        role=UNITS[args.role].label.lower(),
        melee=design.melee,
        missile=design.missile,
        defence=design.defence,
        speed=design.speed,
    )


async def forge_model(call: MortalCall, args: ForgeModelInput) -> str:
    owner = await maker(call, MortalResult.MODEL_REFUSED)
    spec = FAMILIES[args.family]
    knowledge = await KnowledgeMap.load(call.session)
    if not known(spec, knowledge, owner.id):
        fail(MortalResult.MODEL_REFUSED, why=f"{owner.name} does not yet know how to make {an(spec.label.lower())}")
    quality = skilled(await best_skill(call.session, call.me.id, FORGE_SKILLS), await craft_of(call))
    model = await draw_model(call.tick, owner, args.family, world_id=owner.world_id, quality=quality, name=args.name)
    model.description = args.description
    call.target(owner.id)
    await call.record(
        "tools.mortal.forge_model",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.OWNER: owner.id, IncidentRole.PRODUCT: model.entity_id},
        facts={"family": args.family, "quality": quality},
    )
    return result(
        MortalResult.MODEL_FORGED,
        name=model.name,
        family=spec.label.lower(),
        quality=model.quality,
        damage=model.damage,
        protection=model.protection,
    )


async def create_dish(call: MortalCall, args: CreateDishInput) -> str:
    people = await own_people(call, MortalResult.DISH_REFUSED)
    if args.method not in known_methods(await KnowledgeMap.load(call.session), people.id):
        fail(MortalResult.DISH_REFUSED, why=f"{people.name} does not yet cook food {spoken(args.method)}")
    foods = list(dict.fromkeys(food for food in args.ingredients if food in DISH_FOODS))
    if not foods:
        fail(MortalResult.DISH_REFUSED, why="none of those is food: " + ", ".join(food.value for food in DISH_FOODS))
    dish = await found_dish(call.tick, people, args.method, args.course, foods, world_id=people.world_id, name=args.name)
    dish.description = args.description
    call.target(people.id)
    await call.record(
        "tools.mortal.create_dish",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.MEMBER: people.id},
        facts={"dish": dish.name, "method": args.method, "course": args.course, "foods": foods},
    )
    return result(
        MortalResult.DISH_CREATED,
        owner=people.name,
        name=dish.name,
        method=args.method.value,
        course=args.course.value.replace("_", " "),
        ingredients=", ".join(food.value.replace("_", " ") for food in foods),
        nourishment=dish.nourishment,
        delight=dish.delight,
        keeps=dish.keeps,
    )


async def draw_building_type(call: MortalCall, args: DrawStructureTypeInput) -> str:
    people = await own_people(call, MortalResult.STRUCTURE_TYPE_REFUSED)
    if await best_skill(call.session, call.me.id, BUILD_SKILLS) < call.rules.integrity.draw_skill:
        fail(MortalResult.STRUCTURE_TYPE_REFUSED, why="you know too little of building to set out a new kind of building")
    design = await draw_structure_type(call.tick, people, args.structure_kind, world_id=people.world_id, name=args.name, form=args.form, storeys=args.storeys)
    design.description = args.description
    call.target(people.id)
    await call.record(
        "tools.mortal.draw_structure_type",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.OWNER: people.id, IncidentRole.PRODUCT: design.entity_id},
        facts={"structure": args.structure_kind, "storeys": design.storeys},
    )
    form = design.form.value.replace("_", " ") if design.form is not None else "any form"
    return result(
        MortalResult.STRUCTURE_TYPE_DRAWN,
        owner=people.name,
        name=design.name,
        kind=STRUCTURES[args.structure_kind].label.lower(),
        form=form,
        storeys=design.storeys,
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.CREATE_ENTITY, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.DRAFT_UNIT_TYPE, mortal, DraftUnitTypeInput, ToolMeta(ActionKind.DESIGN_UNIT, mortal_standard_action), draft_unit_type),
        ToolSpec(MortalToolId.FORGE_MODEL, mortal, ForgeModelInput, meta, forge_model),
        ToolSpec(MortalToolId.CREATE_DISH, mortal, CreateDishInput, meta, create_dish),
        ToolSpec(MortalToolId.DRAW_STRUCTURE_TYPE, mortal, DrawStructureTypeInput, ToolMeta(ActionKind.BUILD, mortal_standard_action), draw_building_type),
    ]
