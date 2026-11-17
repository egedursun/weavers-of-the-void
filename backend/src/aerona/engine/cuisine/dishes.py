from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cuisine import DISH_FOODS, STAPLE_FOODS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cuisine import FLAVOURS, CommunityDishRow, DishIngredientRow, DishRow, DishStepRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.food_kinds import CuisineRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import GoodCategory, IngredientRole, KindConcept, KindSpread, KindStance, MealSlot
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.collective.embodied import embody
from aerona.engine.context import TickContext
from aerona.engine.couplings.novelty import novelty_of
from aerona.engine.economy.good_kinds import GoodBook, good_book
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.nature.microbes import culture_lift
from aerona.engine.notes import note
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.knowledge import KnowledgeMap, branch_level
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat

M = CookingMethod
D = DishCourse
C = CommodityKind
BASE_MEALS = 2
SKILL_PER_LEVEL = 10
COOKED = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})
METHOD_GATES: MappingProxyType[CookingMethod, tuple[KnowledgeBranch | None, int]] = total(
    CookingMethod,
    {
        M.RAW: (None, 0),
        M.BOILED: (None, 0),
        M.STEWED: (None, 0),
        M.STEAMED: (KnowledgeBranch.AGRICULTURE, 1),
        M.ROASTED: (None, 0),
        M.GRILLED: (None, 0),
        M.BAKED: (KnowledgeBranch.AGRICULTURE, 1),
        M.FRIED: (KnowledgeBranch.AGRICULTURE, 2),
        M.SMOKED: (None, 0),
        M.DRIED: (None, 0),
        M.CURED: (KnowledgeBranch.TRADE, 1),
        M.PICKLED: (KnowledgeBranch.TRADE, 1),
        M.FERMENTED: (KnowledgeBranch.AGRICULTURE, 1),
        M.BRAISED: (KnowledgeBranch.AGRICULTURE, 2),
        M.SIMMERED: (None, 0),
        M.GROUND: (KnowledgeBranch.AGRICULTURE, 1),
        M.PRESSED: (KnowledgeBranch.AGRICULTURE, 2),
        M.CONJURED: (KnowledgeBranch.MAGIC, 1),
        M.FREEZE_DRIED: (KnowledgeBranch.AGRICULTURE, 5),
        M.IRRADIATED: (KnowledgeBranch.METALLURGY, 7),
        M.PRINTED: (KnowledgeBranch.METALLURGY, 7),
        M.SYNTHESISED: (KnowledgeBranch.MEDICINE, 6),
        M.VAT_GROWN: (KnowledgeBranch.BIOMANCY, 1),
        M.INFUSED: (None, 0),
        M.DISTILLED: (KnowledgeBranch.MEDICINE, 2),
        M.CHURNED: (None, 0),
        M.SPROUTED: (KnowledgeBranch.AGRICULTURE, 1),
        M.ALKALI_TREATED: (KnowledgeBranch.AGRICULTURE, 2),
        M.CULTURED: (KnowledgeBranch.AGRICULTURE, 2),
        M.CURED_WITH_MINERAL: (KnowledgeBranch.TRADE, 1),
        M.AGED: (KnowledgeBranch.AGRICULTURE, 1),
        M.EXTRUDED: (KnowledgeBranch.METALLURGY, 6),
        M.PRESSURE_COOKED: (KnowledgeBranch.METALLURGY, 5),
    },
)
METHOD_KEEPS: MappingProxyType[CookingMethod, int] = total(
    CookingMethod,
    {
        M.RAW: 0,
        M.BOILED: 0,
        M.STEWED: 0,
        M.STEAMED: 0,
        M.ROASTED: 1,
        M.GRILLED: 0,
        M.BAKED: 1,
        M.FRIED: 0,
        M.SMOKED: 3,
        M.DRIED: 4,
        M.CURED: 4,
        M.PICKLED: 3,
        M.FERMENTED: 3,
        M.BRAISED: 0,
        M.SIMMERED: 0,
        M.GROUND: 2,
        M.PRESSED: 2,
        M.CONJURED: 0,
        M.FREEZE_DRIED: 6,
        M.IRRADIATED: 6,
        M.PRINTED: 3,
        M.SYNTHESISED: 5,
        M.VAT_GROWN: 3,
        M.INFUSED: 0,
        M.DISTILLED: 6,
        M.CHURNED: 1,
        M.SPROUTED: 0,
        M.ALKALI_TREATED: 2,
        M.CULTURED: 3,
        M.CURED_WITH_MINERAL: 4,
        M.AGED: 5,
        M.EXTRUDED: 3,
        M.PRESSURE_COOKED: 0,
    },
)
COURSE_LABELS: MappingProxyType[DishCourse, str] = total(
    DishCourse,
    {
        D.STAPLE: "Dish",
        D.SIDE: "Side dish",
        D.FESTIVE: "Feast dish",
        D.RITE: "Rite dish",
        D.RATION: "Ration",
        D.DELICACY: "Delicacy",
        D.REMEDY: "Remedy",
        D.DRINK: "Drink",
    },
)


COURSE_SLOTS: MappingProxyType[DishCourse, MealSlot] = total(
    DishCourse,
    {
        D.STAPLE: MealSlot.DAILY_MEAL,
        D.SIDE: MealSlot.DAILY_MEAL,
        D.FESTIVE: MealSlot.FEAST,
        D.RITE: MealSlot.RITE,
        D.RATION: MealSlot.RATION,
        D.DELICACY: MealSlot.SNACK,
        D.REMEDY: MealSlot.REMEDY,
        D.DRINK: MealSlot.DAILY_MEAL,
    },
)
G = GoodCategory
R = IngredientRole
CATEGORY_ROLES: MappingProxyType[GoodCategory, IngredientRole] = total(
    GoodCategory,
    {
        G.GRAIN: R.BASE,
        G.ROOT_AND_TUBER: R.BASE,
        G.VEGETABLE: R.BASE,
        G.LEGUME: R.PROTEIN,
        G.FRUIT: R.GARNISH,
        G.NUT_AND_SEED: R.FAT,
        G.OIL_AND_FAT: R.FAT,
        G.SWEETENER: R.SEASONING,
        G.SEASONING: R.SEASONING,
        G.MINERAL_SEASONING: R.PRESERVATIVE,
        G.MEAT: R.PROTEIN,
        G.FISH_AND_SEAFOOD: R.PROTEIN,
        G.DAIRY: R.FAT,
        G.EGGS: R.BINDER,
        G.INSECTS: R.PROTEIN,
        G.FUNGI: R.BASE,
        G.ALGAE: R.BASE,
        G.OFFAL_AND_BLOOD: R.PROTEIN,
        G.FODDER: R.BASE,
        G.DRINK_BASE: R.LIQUID,
        G.STIMULANT: R.SEASONING,
        G.INTOXICANT: R.LIQUID,
        G.MEDICINE: R.SEASONING,
        G.FIBRE: R.BINDER,
        G.TEXTILE: R.BINDER,
        G.HIDE_AND_LEATHER: R.BINDER,
        G.TIMBER: R.BASE,
        G.FUEL: R.BASE,
        G.ORE: R.BASE,
        G.METAL: R.BASE,
        G.STONE: R.BASE,
        G.CLAY_AND_CERAMIC: R.BASE,
        G.GLASS: R.BASE,
        G.CHEMICAL: R.PRESERVATIVE,
        G.DYE_AND_PIGMENT: R.COLOURING,
        G.SCENT_MATERIAL: R.SEASONING,
        G.REAGENT: R.LEAVENING,
        G.TOOLS: R.BASE,
        G.WEAPONS: R.BASE,
        G.ARMOUR: R.BASE,
        G.GARMENTS: R.BASE,
        G.FURNISHINGS: R.BASE,
        G.CONTAINERS: R.BASE,
        G.INSTRUMENTS: R.BASE,
        G.ORNAMENTS: R.GARNISH,
        G.BOOKS_AND_RECORDS: R.BASE,
        G.MACHINES: R.BASE,
        G.PARTS: R.BASE,
        G.ENERGY_STORE: R.BASE,
        G.DATA: R.BASE,
        G.LIVING_GOODS: R.PROTEIN,
        G.SACRED_GOODS: R.GARNISH,
        G.LUXURIES: R.GARNISH,
        G.LIVESTOCK: R.PROTEIN,
        G.MOUNTS: R.PROTEIN,
    },
)


@dataclass
class KitchenTally:
    invented: int = 0
    cooked: int = 0
    short: int = 0
    rationed: int = 0
    spread: int = 0
    adopted: int = 0
    substituted: int = 0


def known_methods(knowledge: KnowledgeMap, holder_id: int) -> list[CookingMethod]:
    return [method for method, (branch, level) in METHOD_GATES.items() if branch is None or knowledge.level(holder_id, branch) >= level]


async def larder(session: AsyncSession, homes: set[int]) -> dict[CommodityKind, int]:
    found: dict[CommodityKind, int] = {}
    for home in sorted(homes):
        for food in DISH_FOODS:
            found[food] = found.get(food, 0) + await holding(session, home, food)
    return {food: amount for food, amount in found.items() if amount > 0}


def dish_traits(method: CookingMethod, course: DishCourse, chosen: list[CommodityKind], goods: GoodBook | None = None) -> dict[str, int]:
    staple = any(food in STAPLE_FOODS for food in chosen)
    fed = sum((goods or GoodBook()).nourishment(food) for food in chosen) // max(1, len(chosen))
    return {
        "nourishment": clamp_int(20 + (20 if staple else 0) + 5 * len(chosen) + fed // 2, 0, PERCENT),
        "delight": clamp_int(20 + 15 * len(chosen) + (20 if C.HERBS in chosen else 0), 0, PERCENT),
        "keeps": METHOD_KEEPS[method],
        "prestige": clamp_int(10 + (30 if course in {D.DELICACY, D.FESTIVE} else 0), 0, PERCENT),
    }


async def found_dish(
    ctx: TickContext,
    origin: EntityRow | None,
    method: CookingMethod,
    course: DishCourse,
    chosen: list[CommodityKind],
    *,
    world_id: int | None,
    name: str | None = None,
    parent: DishRow | None = None,
    flavours: dict[str, int] | None = None,
) -> DishRow:
    goods = await good_book(ctx.session)
    row = DishRow(
        world_id=world_id,
        name=name or await made_name(ctx.session, ctx.rules, origin, COURSE_LABELS[course], method.value, ctx.epoch),
        origin_node_id=origin.id if origin is not None else None,
        derived_from_id=parent.id if parent is not None else None,
        method=method,
        course=course,
        category=COURSE_SLOTS[course],
        built_in=False,
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
        **dish_traits(method, course, chosen, goods),
        **{flavour: clamp_int(value, 0, PERCENT) for flavour, value in (flavours or {}).items() if flavour in FLAVOURS},
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await embody(ctx.session, row)
    ctx.session.add(DishStepRow(dish_id=row.id, step=1, method=method, duration=1, locked=[]))
    for index, food in enumerate(chosen):
        good = goods.rows.get(food)
        role = CATEGORY_ROLES[good.category] if good is not None else IngredientRole.BASE
        ctx.session.add(
            DishIngredientRow(
                dish_id=row.id, commodity=food, share=max(1, PERCENT // len(chosen) - index), role=role, good_kind_id=good.id if good is not None else None
            )
        )
    await ctx.session.flush()
    return row


async def invent_dish(ctx: TickContext, people: EntityRow, knowledge: KnowledgeMap, homes: set[int], *, course: DishCourse | None = None) -> DishRow | None:
    cuisine = await cuisine_of(ctx.session, people.id)
    goods = await good_book(ctx.session)
    stock = {food: amount for food, amount in (await larder(ctx.session, homes)).items() if not shunned(cuisine, goods, food)}
    if not stock:
        return None
    rng = ctx.rng(f"dish.{people.id}.{ctx.epoch}.{course.value if course is not None else 'any'}")
    methods = known_methods(knowledge, people.id)
    method = rng.pick(methods)
    if cuisine is not None and cuisine.signature_method in methods and rng.chance(ctx.rules.cuisine.signature_pct):
        method = cuisine.signature_method
    ranked = sorted(stock, key=lambda food: (not staple_of(cuisine, goods, food), -stock[food], food.value))
    chosen = ranked[: 1 + rng.below(min(3, len(ranked)))]
    course = course or rng.pick([D.STAPLE, D.STAPLE, D.SIDE, D.FESTIVE, D.RITE, D.RATION, D.DELICACY, D.REMEDY, D.DRINK])
    if METHOD_KEEPS[method] >= ctx.rules.cuisine.ration_keeping and course is D.STAPLE:
        course = D.RATION
    flavours = {flavour: getattr(cuisine, flavour) + rng.below(21) - 10 for flavour in FLAVOURS} if cuisine is not None else None
    row = await found_dish(ctx, people, method, course, chosen, world_id=people.world_id, flavours=flavours)
    await hold_dish(ctx, people.id, row.id, KindStance.MAKES, KindSpread.INVENTED)
    for home in sorted(homes):
        place = await living_entity(ctx.session, home)
        if place is not None and place.entity_type is EntityType.SETTLEMENT and not held(home):
            ctx.session.add(CommunityDishRow(community_entity_id=home, dish_id=row.id, popularity=PERCENT // 2, cooked=0, since_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    return row


async def cuisine_of(session: AsyncSession, people_id: int) -> CuisineRow | None:
    found = await session.scalars(
        select(CuisineRow)
        .join(KindHoldingRow, KindHoldingRow.kind_id == CuisineRow.id)
        .where(
            KindHoldingRow.concept == KindConcept.CUISINE,
            KindHoldingRow.holder_node_id == people_id,
            KindHoldingRow.stance.in_(list(COOKED)),
            CuisineRow.retired.is_(False),
        )
        .order_by(KindHoldingRow.strength.desc(), CuisineRow.id)
        .limit(1)
    )
    return found.first()


def same_category(goods: GoodBook, food: CommodityKind, missing: GoodKindRow) -> bool:
    found = goods.rows.get(food)
    return found is not None and found.category is missing.category


def staple_of(cuisine: CuisineRow | None, goods: GoodBook, food: CommodityKind) -> bool:
    good = goods.rows.get(food)
    return cuisine is not None and good is not None and cuisine.category is good.category


def shunned(cuisine: CuisineRow | None, goods: GoodBook, food: CommodityKind) -> bool:
    good = goods.rows.get(food)
    return cuisine is not None and good is not None and cuisine.taboo_category is good.category


FIRST_COURSES = (D.STAPLE, D.DRINK, D.FESTIVE, D.SIDE, D.RITE, D.RATION, D.DELICACY, D.REMEDY)


async def invent(ctx: TickContext, knowledge: KnowledgeMap, tally: KitchenTally) -> None:
    table = ctx.rules.cuisine
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        known = set(await ctx.session.scalars(select(DishRow.course).where(DishRow.origin_node_id == people.id)))
        missing: list[DishCourse | None] = [course for course in FIRST_COURSES[: table.starting_dishes] if course not in known]
        if not missing and not ctx.rng(f"invent_dish.{people.id}.{ctx.epoch}").chance(table.invent_pct):
            continue
        homes = await homes_of(ctx.session, people)
        for course in missing or [None]:
            dish = await invent_dish(ctx, people, knowledge, homes, course=course)
            if dish is not None:
                tally.invented += 1
                await note(ctx, f"{people.name} came to cook {dish.name}.", key="cuisine.invented", ids=[people.id])


async def ingredients_of(session: AsyncSession, dish_id: int) -> list[DishIngredientRow]:
    return list(await session.scalars(select(DishIngredientRow).where(DishIngredientRow.dish_id == dish_id).order_by(DishIngredientRow.commodity)))


async def cook_one(ctx: TickContext, town: EntityRow, row: CommunityDishRow, dish: DishRow, *, meals: int = BASE_MEALS) -> bool:
    table = ctx.rules.cuisine
    portion = round_half_up(table.portion * row.popularity / PERCENT * meals / BASE_MEALS)
    needs = [(item.commodity, max(1, round_half_up(portion * item.share / PERCENT))) for item in await ingredients_of(ctx.session, dish.id)]
    if not needs:
        return False
    for food, amount in needs:
        if await holding(ctx.session, town.id, food) < amount:
            return False
    ledger = goods_of(ctx.session, ctx.epoch)
    for food, amount in needs:
        await ledger.take_units(town.id, food, amount, GoodsFlow.CONSUMPTION)
    return True


async def savour(ctx: TickContext, town: EntityRow, dish: DishRow, *, skill: int = PERCENT) -> None:
    table = ctx.rules.cuisine
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    skilled = 1.0 if skill >= dish.prep_skill else table.skill_pct / PERCENT
    lift = round_half_up(dish.delight * skilled * table.delight_pct / PERCENT * await culture_lift(ctx.session, ctx.rules, town.id, dish.method, dish.course))
    if profile is not None and dish.course in {D.STAPLE, D.SIDE, D.DRINK, D.FESTIVE} and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest - lift, 0, PERCENT)
    if profile is not None and dish.course in {D.DELICACY, D.FESTIVE} and "prestige" not in profile.locked:
        fresh = await novelty_of(ctx.session, dish.entity_id) / PERCENT
        steps = await ctx.session.scalar(select(func.count()).select_from(DishStepRow).where(DishStepRow.dish_id == dish.id)) or 1
        craft = 1 + (steps - 1) * table.step_prestige_pct / PERCENT
        profile.prestige = clamp_int(profile.prestige + round_half_up(dish.prestige * fresh * craft * table.prestige_pct / PERCENT), 0, PERCENT)
    if dish.course is D.RITE and stat(town, "piety") is not None:
        shift_stat(town, "piety", round_half_up(dish.delight * table.rite_pct / PERCENT))
    if dish.course in {D.STAPLE, D.REMEDY} and stat(town, "prosperity") is not None:
        shift_stat(town, "prosperity", round_half_up(dish.nourishment * table.nourish_pct / PERCENT))


async def kitchen_skill(ctx: TickContext, town: EntityRow, people: EntityRow | None) -> int:
    holders = [town.id] + ([people.id] if people is not None else [])
    levels = [await branch_level(ctx.session, holder, KnowledgeBranch.AGRICULTURE) for holder in holders]
    return min(PERCENT, max(levels) * SKILL_PER_LEVEL)


async def substitute(ctx: TickContext, town: EntityRow, row: CommunityDishRow, dish: DishRow, tally: KitchenTally) -> DishRow | None:
    goods = await good_book(ctx.session)
    stock = await larder(ctx.session, {town.id})
    ingredients = await ingredients_of(ctx.session, dish.id)
    used = {item.commodity for item in ingredients}
    chosen: list[CommodityKind] = []
    for item in ingredients:
        if await holding(ctx.session, town.id, item.commodity) > 0:
            chosen.append(item.commodity)
            continue
        missing = goods.rows.get(item.commodity)
        ranked = sorted(stock, key=lambda food: (-stock[food], food.value))
        kin = [food for food in ranked if food not in used and food not in chosen and missing is not None and same_category(goods, food, missing)]
        if not kin:
            return None
        chosen.append(kin[0])
    if set(chosen) == used:
        return None
    origin = await living_entity(ctx.session, dish.origin_node_id) if dish.origin_node_id is not None else None
    made = await found_dish(
        ctx,
        origin or town,
        dish.method,
        dish.course,
        chosen,
        world_id=dish.world_id,
        parent=dish,
        flavours={flavour: getattr(dish, flavour) for flavour in FLAVOURS},
    )
    ctx.session.add(CommunityDishRow(community_entity_id=town.id, dish_id=made.id, popularity=row.popularity, cooked=0, since_epoch=ctx.epoch, locked=[]))
    if "short_epochs" not in row.locked:
        row.short_epochs = 0
    tally.substituted += 1
    await note(ctx, f"{town.name} came to cook {made.name} in place of {dish.name}.", key="cuisine.substituted", ids=[town.id])
    return made


async def cook_dishes(ctx: TickContext, town: EntityRow, tally: KitchenTally) -> None:
    if held(town.id):
        return
    people = await people_of(ctx.session, town)
    cuisine = await cuisine_of(ctx.session, people.id) if people is not None else None
    meals = cuisine.meals_per_day if cuisine is not None else BASE_MEALS
    skill = await kitchen_skill(ctx, town, people)
    for row in list(
        await ctx.session.scalars(select(CommunityDishRow).where(CommunityDishRow.community_entity_id == town.id).order_by(CommunityDishRow.dish_id))
    ):
        dish = await ctx.session.get(DishRow, row.dish_id)
        if dish is None or dish.retired:
            continue
        if await cook_one(ctx, town, row, dish, meals=meals):
            row.cooked += 1
            tally.cooked += 1
            if "short_epochs" not in row.locked:
                row.short_epochs = 0
            await savour(ctx, town, dish, skill=skill)
            if "popularity" not in row.locked:
                row.popularity = clamp_int(row.popularity + ctx.rules.cuisine.taste_gain, 0, PERCENT)
        else:
            tally.short += 1
            if "short_epochs" not in row.locked:
                row.short_epochs += 1
            if "popularity" not in row.locked:
                row.popularity = clamp_int(row.popularity - ctx.rules.cuisine.taste_loss, 0, PERCENT)
            if row.short_epochs >= ctx.rules.cuisine.shortage_epochs:
                await substitute(ctx, town, row, dish, tally)


async def rations(ctx: TickContext, tally: KitchenTally) -> None:
    table = ctx.rules.cuisine
    for army_row in list(await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))):
        owner = await living_entity(ctx.session, army_row.owner_entity_id)
        profile = await ctx.session.get(ArmyProfileRow, army_row.entity_id)
        if owner is None or profile is None or held(army_row.entity_id) or "supply_days" in profile.locked:
            continue
        people = await people_of(ctx.session, owner)
        origin = people.id if people is not None else owner.id
        best = await ctx.session.scalar(
            select(DishRow.keeps)
            .where(DishRow.origin_node_id == origin, DishRow.course == D.RATION, DishRow.retired.is_(False))
            .order_by(DishRow.keeps.desc())
            .limit(1)
        )
        if best:
            profile.supply_days = min(ctx.rules.logistics.supply_days * 2, profile.supply_days + best * table.ration_days)
            tally.rationed += 1


async def carry_dish(ctx: TickContext, origin: EntityRow, destination: EntityRow) -> bool:
    if held(destination.id) or not ctx.rng(f"dish_spread.{origin.id}.{destination.id}.{ctx.epoch}").chance(ctx.rules.cuisine.spread_pct):
        return False
    known = set(await ctx.session.scalars(select(CommunityDishRow.dish_id).where(CommunityDishRow.community_entity_id == destination.id)))
    offered = await ctx.session.scalar(
        select(CommunityDishRow.dish_id)
        .where(CommunityDishRow.community_entity_id == origin.id, CommunityDishRow.dish_id.not_in(known or {0}))
        .order_by(CommunityDishRow.popularity.desc(), CommunityDishRow.dish_id)
        .limit(1)
    )
    if offered is None:
        return False
    ctx.session.add(CommunityDishRow(community_entity_id=destination.id, dish_id=offered, popularity=PERCENT // 4, cooked=0, since_epoch=ctx.epoch, locked=[]))
    return True


async def hold_dish(ctx: TickContext, holder_id: int, dish_id: int, stance: KindStance, spread: KindSpread) -> None:
    found = await ctx.session.scalar(
        select(KindHoldingRow.id).where(
            KindHoldingRow.concept == KindConcept.DISH, KindHoldingRow.kind_id == dish_id, KindHoldingRow.holder_node_id == holder_id
        )
    )
    if found is None:
        ctx.session.add(
            KindHoldingRow(
                concept=KindConcept.DISH, kind_id=dish_id, holder_node_id=holder_id, stance=stance, strength=60, spread=spread, since_epoch=ctx.epoch, locked=[]
            )
        )


async def adopt_held(ctx: TickContext, tally: KitchenTally) -> None:
    rows = await ctx.session.execute(
        select(KindHoldingRow, EntityRow)
        .join(EntityRow, EntityRow.id == KindHoldingRow.holder_node_id)
        .where(KindHoldingRow.concept == KindConcept.DISH, EntityRow.entity_type == EntityType.PEOPLE, KindHoldingRow.stance.in_(list(COOKED)))
        .order_by(KindHoldingRow.id)
    )
    for holding_row, people in rows.all():
        dish = await ctx.session.get(DishRow, holding_row.kind_id)
        if dish is None or dish.retired or held(people.id):
            continue
        for home in sorted(await homes_of(ctx.session, people)):
            place = await living_entity(ctx.session, home)
            if place is None or place.entity_type is not EntityType.SETTLEMENT or held(home):
                continue
            if await ctx.session.get(CommunityDishRow, (home, dish.id)) is None:
                ctx.session.add(
                    CommunityDishRow(
                        community_entity_id=home, dish_id=dish.id, popularity=holding_row.strength // 2, cooked=0, since_epoch=ctx.epoch, locked=[]
                    )
                )
                tally.adopted += 1
    await ctx.session.flush()


async def run_kitchens(ctx: TickContext) -> KitchenTally:
    tally = KitchenTally()
    knowledge = await KnowledgeMap.load(ctx.session)
    await invent(ctx, knowledge, tally)
    await adopt_held(ctx, tally)
    await rations(ctx, tally)
    return tally
