from sqlalchemy import select

from aerona.catalog.life.cuisine import CATEGORY_ROLES, COURSE_SLOTS
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.cuisine import DishIngredientRow, DishRow, DishStepRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import IngredientRole, KindConcept, KindSpread, KindStance
from aerona.engine.context import TickContext
from aerona.engine.economy.good_kinds import GoodBook, ensure_built_in_goods

FOODWAYS_FIXUP = "w48_goods_and_foodways"


async def first_steps(ctx: TickContext) -> int:
    stepped = set(await ctx.session.scalars(select(DishStepRow.dish_id)))
    added = 0
    for dish in list(await ctx.session.scalars(select(DishRow).order_by(DishRow.id))):
        if "category" not in dish.locked:
            dish.category = COURSE_SLOTS[dish.course]
        if dish.id not in stepped:
            ctx.session.add(DishStepRow(dish_id=dish.id, step=1, method=dish.method, duration=1, locked=[]))
            added += 1
    return added


async def ingredient_goods(ctx: TickContext) -> int:
    goods = await GoodBook.load(ctx.session)
    linked = 0
    for item in list(await ctx.session.scalars(select(DishIngredientRow).where(DishIngredientRow.good_kind_id.is_(None)))):
        good = goods.rows.get(item.commodity)
        if good is not None:
            item.good_kind_id = good.id
            if item.role is IngredientRole.BASE:
                item.role = CATEGORY_ROLES[good.category]
            linked += 1
    return linked


async def makers_hold(ctx: TickContext) -> int:
    known = {(row.kind_id, row.holder_node_id) for row in await ctx.session.scalars(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.DISH))}
    rows = await ctx.session.execute(
        select(DishRow.id, DishRow.origin_node_id).join(EntityRow, EntityRow.id == DishRow.origin_node_id).where(EntityRow.entity_type == EntityType.PEOPLE)
    )
    added = 0
    for dish_id, people_id in rows.all():
        if (dish_id, people_id) in known:
            continue
        ctx.session.add(
            KindHoldingRow(
                concept=KindConcept.DISH,
                kind_id=dish_id,
                holder_node_id=people_id,
                stance=KindStance.MAKES,
                strength=ctx.rules.kinds.founding_strength,
                spread=KindSpread.GENESIS,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        added += 1
    return added


async def foodways_backfill(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, FOODWAYS_FIXUP):
        return 0
    result = {"built_in_goods": await ensure_built_in_goods(ctx.session)}
    result["first_steps"] = await first_steps(ctx)
    result["ingredient_goods"] = await ingredient_goods(ctx)
    result["makers_hold"] = await makers_hold(ctx)
    ctx.session.add(AppliedFixupRow(key=FOODWAYS_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
