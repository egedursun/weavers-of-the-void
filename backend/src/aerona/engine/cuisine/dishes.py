from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cuisine import DISH_FOODS, STAPLE_FOODS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.collective.embodied import embody
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.notes import note
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat

M = CookingMethod
D = DishCourse
C = CommodityKind
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


@dataclass
class KitchenTally:
    invented: int = 0
    cooked: int = 0
    short: int = 0
    rationed: int = 0
    spread: int = 0


def known_methods(knowledge: KnowledgeMap, holder_id: int) -> list[CookingMethod]:
    return [method for method, (branch, level) in METHOD_GATES.items() if branch is None or knowledge.level(holder_id, branch) >= level]


async def larder(session: AsyncSession, homes: set[int]) -> dict[CommodityKind, int]:
    found: dict[CommodityKind, int] = {}
    for home in sorted(homes):
        for food in DISH_FOODS:
            found[food] = found.get(food, 0) + await holding(session, home, food)
    return {food: amount for food, amount in found.items() if amount > 0}


def dish_traits(method: CookingMethod, course: DishCourse, chosen: list[CommodityKind]) -> dict[str, int]:
    staple = any(food in STAPLE_FOODS for food in chosen)
    return {
        "nourishment": clamp_int(30 + (30 if staple else 0) + 5 * len(chosen), 0, PERCENT),
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
) -> DishRow:
    row = DishRow(
        world_id=world_id,
        name=name or await made_name(ctx.session, ctx.rules, origin, COURSE_LABELS[course], method.value, ctx.epoch),
        origin_node_id=origin.id if origin is not None else None,
        method=method,
        course=course,
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
        **dish_traits(method, course, chosen),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await embody(ctx.session, row)
    for index, food in enumerate(chosen):
        ctx.session.add(DishIngredientRow(dish_id=row.id, commodity=food, share=max(1, PERCENT // len(chosen) - index)))
    await ctx.session.flush()
    return row


async def invent_dish(ctx: TickContext, people: EntityRow, knowledge: KnowledgeMap, homes: set[int], *, course: DishCourse | None = None) -> DishRow | None:
    stock = await larder(ctx.session, homes)
    if not stock:
        return None
    rng = ctx.rng(f"dish.{people.id}.{ctx.epoch}.{course.value if course is not None else 'any'}")
    method = rng.pick(known_methods(knowledge, people.id))
    ranked = sorted(stock, key=lambda food: (-stock[food], food.value))
    chosen = ranked[: 1 + rng.below(min(3, len(ranked)))]
    course = course or rng.pick([D.STAPLE, D.STAPLE, D.SIDE, D.FESTIVE, D.RITE, D.RATION, D.DELICACY, D.REMEDY, D.DRINK])
    if METHOD_KEEPS[method] >= ctx.rules.cuisine.ration_keeping and course is D.STAPLE:
        course = D.RATION
    row = await found_dish(ctx, people, method, course, chosen, world_id=people.world_id)
    for home in sorted(homes):
        place = await living_entity(ctx.session, home)
        if place is not None and place.entity_type is EntityType.SETTLEMENT and not held(home):
            ctx.session.add(CommunityDishRow(community_entity_id=home, dish_id=row.id, popularity=PERCENT // 2, cooked=0, since_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    return row


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


async def cook_one(ctx: TickContext, town: EntityRow, row: CommunityDishRow, dish: DishRow) -> bool:
    table = ctx.rules.cuisine
    portion = round_half_up(table.portion * row.popularity / PERCENT)
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


async def savour(ctx: TickContext, town: EntityRow, dish: DishRow) -> None:
    table = ctx.rules.cuisine
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    lift = round_half_up(dish.delight * table.delight_pct / PERCENT)
    if profile is not None and dish.course in {D.STAPLE, D.SIDE, D.DRINK, D.FESTIVE} and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest - lift, 0, PERCENT)
    if profile is not None and dish.course in {D.DELICACY, D.FESTIVE} and "prestige" not in profile.locked:
        profile.prestige = clamp_int(profile.prestige + round_half_up(dish.prestige * table.prestige_pct / PERCENT), 0, PERCENT)
    if dish.course is D.RITE and stat(town, "piety") is not None:
        shift_stat(town, "piety", round_half_up(dish.delight * table.rite_pct / PERCENT))
    if dish.course in {D.STAPLE, D.REMEDY} and stat(town, "prosperity") is not None:
        shift_stat(town, "prosperity", round_half_up(dish.nourishment * table.nourish_pct / PERCENT))


async def cook_dishes(ctx: TickContext, town: EntityRow, tally: KitchenTally) -> None:
    if held(town.id):
        return
    for row in list(
        await ctx.session.scalars(select(CommunityDishRow).where(CommunityDishRow.community_entity_id == town.id).order_by(CommunityDishRow.dish_id))
    ):
        dish = await ctx.session.get(DishRow, row.dish_id)
        if dish is None or dish.retired:
            continue
        if await cook_one(ctx, town, row, dish):
            row.cooked += 1
            tally.cooked += 1
            await savour(ctx, town, dish)
            if "popularity" not in row.locked:
                row.popularity = clamp_int(row.popularity + ctx.rules.cuisine.taste_gain, 0, PERCENT)
        else:
            tally.short += 1
            if "popularity" not in row.locked:
                row.popularity = clamp_int(row.popularity - ctx.rules.cuisine.taste_loss, 0, PERCENT)


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


async def run_kitchens(ctx: TickContext) -> KitchenTally:
    tally = KitchenTally()
    knowledge = await KnowledgeMap.load(ctx.session)
    await invent(ctx, knowledge, tally)
    await rations(ctx, tally)
    return tally
