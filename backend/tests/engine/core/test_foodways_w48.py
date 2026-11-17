from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.cuisine import CommunityDishRow, DishIngredientRow, DishRow, DishStepRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.food_kinds import CuisineRow, DrinkKindRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import DrinkCategory, DrinkRole, GoodCategory, GoodLegality, GoodTaxClass, IngredientRole, KindConcept, KindStance, MealSlot
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.cuisine.cuisines import keep_cuisines
from aerona.engine.cuisine.dishes import KitchenTally, cook_dishes, found_dish, invent_dish, savour
from aerona.engine.cuisine.drinks import drink_safety, keep_drinks
from aerona.engine.cuisine.legacy import foodways_backfill
from aerona.engine.economy.good_kinds import GoodBook, ensure_built_in_goods
from aerona.engine.economy.markets import price_of
from aerona.engine.kinds.life import keep_kinds
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules

CERTAIN = tuned_rules(
    kinds={"spread_pct": 100, "adoption_strength": 80},
    drink={"derive_pct": 100, "derive_strength": 50},
    cuisine={"fusion_pct": 100, "fusion_strength": 50, "founding_dishes": 2, "shortage_epochs": 1},
)


async def people_with_town(session: AsyncSession, world: CoreWorld, name: str, region: int = 0) -> tuple[object, object]:
    folk = await entity(session, name, EntityType.PEOPLE, PeopleStats(population=4000), world_id=world.world.id)
    town = await settlement(session, f"{name} town", world, world.regions[region])
    await bond(session, town.id, folk.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, crime=10, unrest=40))
    await session.flush()
    return folk, town


async def test_every_legacy_commodity_becomes_a_built_in_good_once(session: AsyncSession, world: CoreWorld) -> None:
    assert await ensure_built_in_goods(session) == len(CommodityKind)
    assert await ensure_built_in_goods(session) == 0
    book = await GoodBook.load(session)
    assert set(book.rows) == set(CommodityKind)
    assert all(row.built_in and row.world_id is None for row in book.rows.values())


async def test_a_good_kind_sets_the_price_demand_tariff_and_spoilage_of_its_goods(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "goods")
    await ensure_built_in_goods(session)
    book = await GoodBook.load(session)
    grain = book.rows[CommodityKind.GRAIN]
    before = price_of(ctx, CommodityKind.GRAIN, 100, 100, 1.0, base_price=book.base_price(CommodityKind.GRAIN))
    grain.base_value *= 2
    assert price_of(ctx, CommodityKind.GRAIN, 100, 100, 1.0, base_price=book.base_price(CommodityKind.GRAIN)) == before * 2
    free = book.demand_scale(ctx.rules, CommodityKind.GRAIN, prosperity=50, piety=0)
    grain.legality = GoodLegality.FORBIDDEN
    assert book.demand_scale(ctx.rules, CommodityKind.GRAIN, prosperity=50, piety=0) < free
    grain.tax_class = GoodTaxClass.EXEMPT
    assert book.tariff_scale(ctx.rules, CommodityKind.GRAIN) == 0
    grain.perishability = 0
    assert book.spoil_scale(CommodityKind.GRAIN) == 0
    incense = book.rows[CommodityKind.INCENSE]
    assert book.demand_scale(ctx.rules, CommodityKind.INCENSE, prosperity=50, piety=90) > book.demand_scale(
        ctx.rules, CommodityKind.INCENSE, prosperity=50, piety=0
    )
    assert incense.sacred > 0


async def test_a_new_dish_has_its_method_as_step_one_a_meal_slot_and_ingredient_roles(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "dish")
    await ensure_built_in_goods(session)
    folk, _ = await people_with_town(session, world, "Ardan")
    dish = await found_dish(ctx, folk, CookingMethod.BAKED, DishCourse.FESTIVE, [CommodityKind.GRAIN, CommodityKind.MEAT], world_id=world.world.id)
    steps = list(await session.scalars(select(DishStepRow).where(DishStepRow.dish_id == dish.id)))
    assert [(step.step, step.method) for step in steps] == [(1, CookingMethod.BAKED)]
    assert dish.category is MealSlot.FEAST
    roles = {item.commodity: item.role for item in await session.scalars(select(DishIngredientRow).where(DishIngredientRow.dish_id == dish.id))}
    assert roles == {CommodityKind.GRAIN: IngredientRole.BASE, CommodityKind.MEAT: IngredientRole.PROTEIN}


async def test_a_dish_without_its_scarce_good_gives_way_to_a_derived_dish(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "kitchens", rules=CERTAIN)
    await ensure_built_in_goods(session)
    folk, town = await people_with_town(session, world, "Ardan")
    dish = await found_dish(ctx, folk, CookingMethod.STEWED, DishCourse.STAPLE, [CommodityKind.MILK], world_id=world.world.id)
    session.add(CommunityDishRow(community_entity_id=town.id, dish_id=dish.id, popularity=60, cooked=0, since_epoch=0, locked=[]))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.CHEESE, quantity=500))
    await session.flush()
    tally = KitchenTally()
    await cook_dishes(ctx, town, tally)
    derived = await session.scalar(select(DishRow).where(DishRow.derived_from_id == dish.id))
    assert derived is not None and tally.substituted == 1
    used = set(await session.scalars(select(DishIngredientRow.commodity).where(DishIngredientRow.dish_id == derived.id)))
    assert used == {CommodityKind.CHEESE}
    assert await session.get(CommunityDishRow, (town.id, derived.id)) is not None


async def test_the_borrowed_feast(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "foodways", rules=CERTAIN)
    host, host_town = await people_with_town(session, world, "Ardan")
    guest, guest_town = await people_with_town(session, world, "Belis", region=1)
    await bond(session, host.id, guest.id, BondKind.TRADES_WITH)
    session.add(CommunityStockRow(community_entity_id=host_town.id, commodity=CommodityKind.BREW_BASE, quantity=200))
    await session.flush()
    await keep_drinks(ctx)
    drink = await session.scalar(select(DrinkKindRow).where(DrinkKindRow.origin_node_id == host.id))
    assert drink is not None and drink.category is DrinkCategory.FERMENTED and drink.water_safety > 0
    drink.role = DrinkRole.HOSPITALITY
    made = await session.scalar(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.DRINK, KindHoldingRow.kind_id == drink.id))
    assert made is not None and made.stance is KindStance.MAKES
    made.strength = 100
    await keep_kinds(ctx)
    taken = await session.scalar(
        select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.DRINK, KindHoldingRow.kind_id == drink.id, KindHoldingRow.holder_node_id == guest.id)
    )
    assert taken is not None and taken.stance is KindStance.USES
    await keep_drinks(ctx)
    own = await session.scalar(select(DrinkKindRow).where(DrinkKindRow.origin_node_id == guest.id, DrinkKindRow.derived_from_id == drink.id))
    assert own is not None
    safety = await drink_safety(session)
    assert safety[guest_town.id] == own.water_safety > 0
    rules = Rules()
    assert 1 - safety[guest_town.id] * rules.drink.water_safety_pct / 10000 < 1


async def test_a_people_with_dishes_comes_to_a_cuisine_that_fuses_with_a_neighbours(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cuisine", rules=CERTAIN)
    await ensure_built_in_goods(session)
    first, first_town = await people_with_town(session, world, "Ardan")
    second, _ = await people_with_town(session, world, "Belis", region=1)
    await bond(session, first.id, second.id, BondKind.TRADES_WITH)
    for people, foods in ((first, [CommodityKind.GRAIN]), (second, [CommodityKind.FISH])):
        for course in (DishCourse.STAPLE, DishCourse.FESTIVE):
            await found_dish(ctx, people, CookingMethod.BOILED, course, foods, world_id=world.world.id, flavours={"sweet": 60 if people is first else 10})
    await keep_cuisines(ctx)
    cuisines = {row.origin_node_id: row for row in await session.scalars(select(CuisineRow))}
    assert set(cuisines) == {first.id, second.id}
    assert cuisines[first.id].sweet == 60 and cuisines[first.id].category is GoodCategory.GRAIN
    profile = await session.get(SettlementProfileRow, first_town.id)
    assert profile is not None and profile.unrest < 40
    for holding_row in await session.scalars(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.CUISINE)):
        holding_row.strength = 100
    await keep_kinds(ctx)
    await keep_cuisines(ctx)
    fused = list(await session.scalars(select(CuisineRow).where(CuisineRow.derived_from_id.is_not(None))))
    assert fused and all(row.sweet == 35 for row in fused)


async def test_a_cuisine_that_shuns_a_food_keeps_it_out_of_new_dishes(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cuisine", rules=CERTAIN)
    await ensure_built_in_goods(session)
    folk, town = await people_with_town(session, world, "Ardan")
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.MEAT, quantity=900))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=100))
    cuisine = CuisineRow(
        name="Ardan way", category=GoodCategory.GRAIN, origin_node_id=folk.id, world_id=world.world.id, taboo_category=GoodCategory.MEAT, locked=[]
    )
    session.add(cuisine)
    await session.flush()
    session.add(KindHoldingRow(concept=KindConcept.CUISINE, kind_id=cuisine.id, holder_node_id=folk.id, stance=KindStance.MAKES, strength=60, locked=[]))
    await session.flush()
    for _ in range(4):
        dish = await invent_dish(ctx, folk, await KnowledgeMap.load(session), {town.id})
        assert dish is not None
        used = set(await session.scalars(select(DishIngredientRow.commodity).where(DishIngredientRow.dish_id == dish.id)))
        assert CommodityKind.MEAT not in used


async def test_the_legacy_pass_gives_old_dishes_steps_goods_and_makers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "legacy")
    folk, _ = await people_with_town(session, world, "Ardan")
    dish = DishRow(name="Old pot", method=CookingMethod.SMOKED, course=DishCourse.RATION, origin_node_id=folk.id, world_id=world.world.id, locked=[])
    session.add(dish)
    await session.flush()
    session.add(DishIngredientRow(dish_id=dish.id, commodity=CommodityKind.FISH, share=100))
    await session.flush()
    assert await foodways_backfill(ctx) > 0
    assert await foodways_backfill(ctx) == 0
    assert dish.category is MealSlot.RATION
    assert await session.scalar(select(func.count()).select_from(GoodKindRow).where(GoodKindRow.built_in.is_(True))) == len(CommodityKind)
    item = await session.get(DishIngredientRow, (dish.id, CommodityKind.FISH))
    assert item is not None and item.good_kind_id is not None and item.role is IngredientRole.PROTEIN
    step = await session.scalar(select(DishStepRow).where(DishStepRow.dish_id == dish.id))
    assert step is not None and step.method is CookingMethod.SMOKED
    maker = await session.scalar(select(KindHoldingRow).where(KindHoldingRow.concept == KindConcept.DISH, KindHoldingRow.kind_id == dish.id))
    assert maker is not None and maker.holder_node_id == folk.id


def test_goods_dishes_drinks_and_cuisines_are_kinds_of_things() -> None:
    assert {KindConcept.GOOD, KindConcept.DISH, KindConcept.DRINK, KindConcept.CUISINE} <= set(CONCEPTS)
    for concept in (KindConcept.GOOD, KindConcept.DISH, KindConcept.DRINK, KindConcept.CUISINE):
        spec = CONCEPTS[concept]
        columns = set(spec.table.__table__.columns.keys())
        assert {item.column for item in spec.properties} <= columns
        assert set(spec.category_labels) == {value.value for value in spec.category}


async def test_a_feast_dish_of_more_steps_lends_its_town_more_prestige(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "kitchens")
    await ensure_built_in_goods(session)
    folk, town = await people_with_town(session, world, "Ardan")
    plain = await found_dish(ctx, folk, CookingMethod.BAKED, DishCourse.FESTIVE, [CommodityKind.GRAIN], world_id=world.world.id)
    worked = await found_dish(ctx, folk, CookingMethod.BAKED, DishCourse.FESTIVE, [CommodityKind.GRAIN], world_id=world.world.id)
    for step in (2, 3):
        session.add(DishStepRow(dish_id=worked.id, step=step, method=CookingMethod.AGED, duration=4, locked=[]))
    await session.flush()
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None
    gains = []
    for dish in (plain, worked):
        profile.prestige = 10
        await savour(ctx, town, dish)
        gains.append(profile.prestige - 10)
    assert gains[1] > gains[0]
