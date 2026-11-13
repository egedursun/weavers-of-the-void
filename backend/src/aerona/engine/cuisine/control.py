from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.cuisine import DISH_FIELDS, CommunityDishRow, DishIngredientRow, DishRow
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind
from aerona.engine.collective.embodied import settle, unmake
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import found_dish
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found

EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "dish": (DishRow, DISH_FIELDS, "dish"),
    "community_dish": (CommunityDishRow, ("popularity", "cooked"), "dish of a community"),
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


async def set_ingredient(ctx: TickContext, dish_id: int, commodity: CommodityKind, share: int) -> DishIngredientRow:
    await found(ctx, DishRow, dish_id, "dish")
    row = await ctx.session.get(DishIngredientRow, (dish_id, commodity))
    if row is None:
        row = DishIngredientRow(dish_id=dish_id, commodity=commodity, share=1)
        ctx.session.add(row)
    row.share = max(1, min(100, share))
    await ctx.session.flush()
    return row


async def remove_ingredient(ctx: TickContext, dish_id: int, commodity: CommodityKind) -> None:
    await ctx.session.delete(await found(ctx, DishIngredientRow, (dish_id, commodity), "ingredient"))
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
