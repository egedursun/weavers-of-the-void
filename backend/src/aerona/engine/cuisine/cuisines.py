from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cuisine import FLAVOURS, DishIngredientRow, DishRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.food_kinds import CuisineRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import GoodCategory, KindConcept, KindSpread, KindStance
from aerona.engine.context import TickContext
from aerona.engine.cuisine.dishes import COOKED, cuisine_of
from aerona.engine.economy.good_kinds import good_book
from aerona.engine.notes import note
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat

CUISINE_WORD = "Cuisine"


@dataclass
class CuisineTally:
    founded: int = 0
    fused: int = 0
    feasted: int = 0


def mean_taste(rows: list[DishRow] | list[CuisineRow]) -> dict[str, int]:
    return {flavour: round_half_up(sum(getattr(row, flavour) for row in rows) / max(1, len(rows))) for flavour in FLAVOURS}


async def own_dishes(ctx: TickContext, people_id: int) -> list[DishRow]:
    return list(await ctx.session.scalars(select(DishRow).where(DishRow.origin_node_id == people_id, DishRow.retired.is_(False)).order_by(DishRow.id)))


async def staple_category(ctx: TickContext, dishes: list[DishRow]) -> GoodCategory:
    goods = await good_book(ctx.session)
    weights: Counter[GoodCategory] = Counter()
    found = await ctx.session.scalars(select(DishIngredientRow).where(DishIngredientRow.dish_id.in_([dish.id for dish in dishes])))
    for item in found:
        good = goods.rows.get(item.commodity)
        if good is not None:
            weights[good.category] += item.share
    return max(sorted(weights), key=lambda category: weights[category]) if weights else GoodCategory.GRAIN


def signature(dishes: list[DishRow]) -> CookingMethod:
    methods = Counter(dish.method for dish in dishes)
    return max(sorted(methods), key=lambda method: methods[method]) if methods else CookingMethod.BOILED


async def hold_cuisine(ctx: TickContext, people_id: int, cuisine_id: int, spread: KindSpread) -> None:
    ctx.session.add(
        KindHoldingRow(
            concept=KindConcept.CUISINE,
            kind_id=cuisine_id,
            holder_node_id=people_id,
            stance=KindStance.MAKES,
            strength=ctx.rules.kinds.founding_strength,
            spread=spread,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )


async def found_cuisine(ctx: TickContext, people: EntityRow, tally: CuisineTally) -> CuisineRow | None:
    if await ctx.session.scalar(select(CuisineRow.id).where(CuisineRow.origin_node_id == people.id).limit(1)) is not None:
        return None
    dishes = await own_dishes(ctx, people.id)
    if len(dishes) < ctx.rules.cuisine.founding_dishes:
        return None
    feasts = sum(1 for dish in dishes if dish.prestige >= PERCENT // 4)
    row = CuisineRow(
        name=await made_name(ctx.session, ctx.rules, people, CUISINE_WORD, "cuisine", ctx.epoch),
        category=await staple_category(ctx, dishes),
        world_id=people.world_id,
        origin_node_id=people.id,
        signature_method=signature(dishes),
        etiquette=clamp_int(sum(dish.prestige for dish in dishes) // len(dishes), 0, PERCENT),
        meals_per_day=2,
        feasting=clamp_int(feasts * PERCENT // len(dishes), 0, PERCENT),
        built_in=False,
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
        **mean_taste(dishes),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await hold_cuisine(ctx, people.id, row.id, KindSpread.INVENTED)
    tally.founded += 1
    await note(ctx, f"The way the {people.name} eat came to be known as {row.name}.", key="cuisine.founded", ids=[people.id])
    return row


async def fuse(ctx: TickContext, people: EntityRow, tally: CuisineTally) -> None:
    table = ctx.rules.cuisine
    own = await ctx.session.scalar(
        select(CuisineRow).where(CuisineRow.origin_node_id == people.id, CuisineRow.retired.is_(False)).order_by(CuisineRow.id.desc())
    )
    if own is None:
        return
    rows = await ctx.session.execute(
        select(KindHoldingRow, CuisineRow)
        .join(CuisineRow, CuisineRow.id == KindHoldingRow.kind_id)
        .where(KindHoldingRow.concept == KindConcept.CUISINE, KindHoldingRow.holder_node_id == people.id, CuisineRow.origin_node_id != people.id)
        .order_by(KindHoldingRow.id)
    )
    for holding_row, foreign in rows.all():
        if holding_row.stance not in COOKED or holding_row.strength < table.fusion_strength or foreign.retired:
            continue
        if await ctx.session.scalar(select(CuisineRow.id).where(CuisineRow.derived_from_id == foreign.id, CuisineRow.origin_node_id == people.id)) is not None:
            continue
        if not ctx.rng(f"cuisine.fuse.{people.id}.{foreign.id}.{ctx.epoch}").chance(table.fusion_pct):
            continue
        fused = CuisineRow(
            name=await made_name(ctx.session, ctx.rules, people, CUISINE_WORD, "fusion", foreign.id, ctx.epoch),
            category=own.category,
            world_id=people.world_id,
            origin_node_id=people.id,
            derived_from_id=foreign.id,
            signature_method=foreign.signature_method,
            taboo_category=own.taboo_category,
            etiquette=(own.etiquette + foreign.etiquette) // 2,
            meals_per_day=own.meals_per_day,
            feasting=(own.feasting + foreign.feasting) // 2,
            built_in=False,
            created_epoch=ctx.epoch,
            retired=False,
            locked=[],
            **mean_taste([own, foreign]),
        )
        ctx.session.add(fused)
        await ctx.session.flush()
        await hold_cuisine(ctx, people.id, fused.id, KindSpread.CONTACT)
        tally.fused += 1
        await note(ctx, f"The {people.name} came to eat in a way that joins {own.name} and {foreign.name}: {fused.name}.", key="cuisine.fused", ids=[people.id])


async def feast(ctx: TickContext, people: EntityRow, tally: CuisineTally) -> None:
    cuisine = await cuisine_of(ctx.session, people.id)
    if cuisine is None:
        return
    table = ctx.rules.cuisine
    for home in sorted(await homes_of(ctx.session, people)):
        town = await ctx.session.get(EntityRow, home)
        if town is None or town.entity_type is not EntityType.SETTLEMENT or held(home):
            continue
        profile = await ctx.session.get(SettlementProfileRow, home)
        if profile is not None and "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest - round_half_up(cuisine.feasting * table.feasting_unrest_pct / PERCENT), 0, PERCENT)
        if profile is not None and "prestige" not in profile.locked:
            gained = round_half_up(cuisine.etiquette * cuisine.feasting / PERCENT * table.etiquette_prestige_pct / PERCENT)
            profile.prestige = clamp_int(profile.prestige + gained, 0, PERCENT)
        shift_stat(town, "prosperity", -round_half_up(cuisine.feasting * table.feasting_cost_pct / PERCENT), low=0, high=PERCENT)
        tally.feasted += 1


async def keep_cuisines(ctx: TickContext) -> CuisineTally:
    tally = CuisineTally()
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        await found_cuisine(ctx, people, tally)
        await fuse(ctx, people, tally)
        await feast(ctx, people, tally)
    await ctx.session.flush()
    return tally
