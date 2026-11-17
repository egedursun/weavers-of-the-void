from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.cuisine import DISH_FIELDS, STEP_FIELDS, CommunityDishRow, DishIngredientRow, DishRow, DishStepRow
from aerona.db.tables.kinds import GoodKindRow
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import IngredientRole
from aerona.engine.collective.embodied import settle, unmake
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import found_dish
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found

EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "dish": (DishRow, DISH_FIELDS, "dish"),
    "community_dish": (CommunityDishRow, ("popularity", "cooked", "short_epochs"), "dish of a community"),
    "dish_step": (DishStepRow, STEP_FIELDS, "step of a dish"),
}


async def new_dish(
    ctx: TickContext,
    origin_id: int | None,
    method: CookingMethod,
    course: DishCourse,
    *,
    world_id: int | None,
    name: str | None,
    ingredients: list[CommodityKind],
) -> DishRow:
    origin = await entity(ctx, origin_id, "maker") if origin_id is not None else None
    if origin is None and world_id is None:
        raise ValidationFailedError("A dish needs a maker or a world.")
    world = world_id if world_id is not None else (origin.world_id if origin is not None else None)
    return await found_dish(ctx, origin, method, course, list(dict.fromkeys(ingredients)), world_id=world, name=name)


async def set_ingredient(
    ctx: TickContext,
    dish_id: int,
    commodity: CommodityKind,
    share: int,
    *,
    role: IngredientRole = IngredientRole.BASE,
    good_kind_id: int | None = None,
) -> DishIngredientRow:
    await found(ctx, DishRow, dish_id, "dish")
    if good_kind_id is not None:
        await found(ctx, GoodKindRow, good_kind_id, "good")
    row = await ctx.session.get(DishIngredientRow, (dish_id, commodity))
    if row is None:
        row = DishIngredientRow(dish_id=dish_id, commodity=commodity, share=1)
        ctx.session.add(row)
    row.share = max(1, min(100, share))
    row.role = role
    row.good_kind_id = good_kind_id
    await ctx.session.flush()
    return row


async def set_step(ctx: TickContext, dish_id: int, step: int, method: CookingMethod, duration: int) -> DishStepRow:
    await found(ctx, DishRow, dish_id, "dish")
    row = await ctx.session.scalar(select(DishStepRow).where(DishStepRow.dish_id == dish_id, DishStepRow.step == step))
    if row is None:
        row = DishStepRow(dish_id=dish_id, step=step, method=method, duration=duration, locked=[])
        ctx.session.add(row)
    apply(row, {"method": method, "duration": duration}, [])
    await ctx.session.flush()
    return row


async def remove_ingredient(ctx: TickContext, dish_id: int, commodity: CommodityKind) -> None:
    await ctx.session.delete(await found(ctx, DishIngredientRow, (dish_id, commodity), "ingredient"))
    await ctx.session.flush()


async def remove_step(ctx: TickContext, step_id: int) -> None:
    row = await found(ctx, DishStepRow, step_id, "step of a dish")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def cook_in(ctx: TickContext, community_id: int, dish_id: int, popularity: int) -> CommunityDishRow:
    await entity(ctx, community_id, "community")
    await found(ctx, DishRow, dish_id, "dish")
    row = await ctx.session.get(CommunityDishRow, (community_id, dish_id))
    if row is None:
        row = CommunityDishRow(community_entity_id=community_id, dish_id=dish_id, popularity=50, cooked=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, {"popularity": popularity}, [])
    await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    await settle(ctx.session, row)
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    row = await found(ctx, table, key, label)
    await unmake(ctx.session, row)
    await ctx.session.delete(row)
    await ctx.session.flush()
