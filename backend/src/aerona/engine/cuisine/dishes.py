from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cuisine import DISH_FOODS, STAPLE_FOODS
from aerona.catalog.life.cuisine import (
    CATEGORY_ROLES,
    COURSE_LABELS,
    COURSE_SLOTS,
    DISH_TRAITS_DISH_COURSES,
    FIRST_COURSES,
    INVENT_DISH_DISH_COURSES,
    METHOD_GATES,
    METHOD_KEEPS,
    SAVOUR_DISH_COURSES,
    SAVOUR_DISH_COURSES_2,
    SAVOUR_DISH_COURSES_3,
)
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
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
from aerona.domain.enums.kinds import IngredientRole, KindConcept, KindSpread, KindStance
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.collective.embodied import embody
from aerona.engine.context import TickContext
from aerona.engine.couplings.novelty import novelty_of
from aerona.engine.economy.good_kinds import GoodBook, good_book
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.nature.microbes import culture_lift
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.knowledge import KnowledgeMap, branch_level
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import StepDraft, record

D = DishCourse
C = CommodityKind
BASE_MEALS = 2
SKILL_PER_LEVEL = 10
COOKED = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})


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
        "prestige": clamp_int(10 + (30 if course in DISH_TRAITS_DISH_COURSES else 0), 0, PERCENT),
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
    course = course or rng.pick(INVENT_DISH_DISH_COURSES)
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


@memoized(CuisineRow, KindHoldingRow)
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


async def invent(ctx: TickContext, knowledge: KnowledgeMap, tally: KitchenTally) -> None:
    table = ctx.rules.cuisine
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        cooked = list(await ctx.session.scalars(select(DishRow.course).where(DishRow.origin_node_id == people.id).order_by(DishRow.id)))
        known = set(cooked)
        missing: list[DishCourse | None] = [course for course in FIRST_COURSES[: table.starting_dishes] if course not in known]
        missing += [None] if not missing and len(cooked) < table.starting_dishes else []
        if not missing and not ctx.rng(f"invent_dish.{people.id}.{ctx.epoch}").chance(table.invent_pct):
            continue
        homes = await homes_of(ctx.session, people)
        for course in missing or [None]:
            dish = await invent_dish(ctx, people, knowledge, homes, course=course)
            if dish is not None:
                tally.invented += 1
                await record(
                    ctx,
                    "cuisine.invented",
                    roles={IncidentRole.MAKER: people.id},
                    facts={"dish": dish.name, "course": dish.course, "method": dish.method},
                    steps=(StepDraft(StepAction.PREPARE, actor=people.id),),
                )


@memoized(DishIngredientRow)
async def ingredient_index(session: AsyncSession) -> dict[int, tuple[DishIngredientRow, ...]]:
    found: dict[int, list[DishIngredientRow]] = defaultdict(list)
    for row in await session.scalars(select(DishIngredientRow).order_by(DishIngredientRow.dish_id, DishIngredientRow.commodity)):
        found[row.dish_id].append(row)
    return {dish_id: tuple(rows) for dish_id, rows in found.items()}


async def ingredients_of(session: AsyncSession, dish_id: int) -> list[DishIngredientRow]:
    return list((await ingredient_index(session)).get(dish_id, ()))


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
    if profile is not None and dish.course in SAVOUR_DISH_COURSES and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest - lift, 0, PERCENT)
    if profile is not None and dish.course in SAVOUR_DISH_COURSES_2 and "prestige" not in profile.locked:
        fresh = await novelty_of(ctx.session, dish.entity_id) / PERCENT
        steps = await ctx.session.scalar(select(func.count()).select_from(DishStepRow).where(DishStepRow.dish_id == dish.id)) or 1
        craft = 1 + (steps - 1) * table.step_prestige_pct / PERCENT
        profile.prestige = clamp_int(profile.prestige + round_half_up(dish.prestige * fresh * craft * table.prestige_pct / PERCENT), 0, PERCENT)
    if dish.course is D.RITE and stat(town, "piety") is not None:
        shift_stat(town, "piety", round_half_up(dish.delight * table.rite_pct / PERCENT))
    if dish.course in SAVOUR_DISH_COURSES_3 and stat(town, "prosperity") is not None:
        shift_stat(town, "prosperity", round_half_up(dish.nourishment * table.nourish_pct / PERCENT))


async def kitchen_skill(ctx: TickContext, town: EntityRow, people: EntityRow | None, knowledge: KnowledgeMap | None = None) -> int:
    holders = [town.id] + ([people.id] if people is not None else [])
    if knowledge is not None:
        levels = [knowledge.level(holder, KnowledgeBranch.AGRICULTURE) for holder in holders]
    else:
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
    await record(
        ctx,
        "cuisine.substituted",
        roles={IncidentRole.MAKER: town.id, IncidentRole.ORIGIN: dish.origin_node_id},
        facts={"dish": made.name, "replaced": dish.name, "method": dish.method},
        steps=(StepDraft(StepAction.PREPARE, actor=town.id),),
        place=town.id,
    )
    return made


async def cook_dishes(ctx: TickContext, town: EntityRow, tally: KitchenTally, knowledge: KnowledgeMap | None = None) -> None:
    if held(town.id):
        return
    people = await people_of(ctx.session, town)
    cuisine = await cuisine_of(ctx.session, people.id) if people is not None else None
    meals = cuisine.meals_per_day if cuisine is not None else BASE_MEALS
    skill = await kitchen_skill(ctx, town, people, knowledge)
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
    found = rows.all()
    pairs = await ctx.session.execute(select(CommunityDishRow.community_entity_id, CommunityDishRow.dish_id)) if found else None
    cooked: set[tuple[int, int]] = {(home, dish) for home, dish in pairs} if pairs is not None else set()
    for holding_row, people in found:
        dish = await ctx.session.get(DishRow, holding_row.kind_id)
        if dish is None or dish.retired or held(people.id):
            continue
        for home in sorted(await homes_of(ctx.session, people)):
            place = await living_entity(ctx.session, home)
            if place is None or place.entity_type is not EntityType.SETTLEMENT or held(home):
                continue
            if (home, dish.id) not in cooked:
                cooked.add((home, dish.id))
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
