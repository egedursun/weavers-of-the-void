from aerona.catalog.commodities import COMMODITIES, base_price
from aerona.catalog.flora import PLANT_PRODUCTS
from aerona.catalog.good_builtins import BUILT_IN_GOODS
from aerona.db.tables.economy import WorkshopRow
from aerona.domain.enums.ecology import PlantYield
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.markets import price_of
from aerona.engine.economy.stocks import holding
from aerona.engine.economy.w52_goods import seed_new_goods
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, settlement, tuned

NEW = (
    CommodityKind.OIL,
    CommodityKind.SUGAR,
    CommodityKind.SPICE,
    CommodityKind.HALITE,
    CommodityKind.HONEY,
    CommodityKind.WAX,
    CommodityKind.POTTERY,
    CommodityKind.BOOKS,
)


def test_forty_three_goods_each_with_category_price_and_use() -> None:
    assert len(CommodityKind) == 43 and all(kind in COMMODITIES and kind in BUILT_IN_GOODS for kind in NEW)
    rules = Rules()
    assert all(base_price(rules, kind) == COMMODITIES[kind].base_price for kind in CommodityKind)


def test_plant_products_now_reach_their_own_goods() -> None:
    by_yield = {item.product: item.commodity for item in PLANT_PRODUCTS.values()}
    assert (
        by_yield[PlantYield.OIL] is CommodityKind.OIL
        and by_yield[PlantYield.SPICE] is CommodityKind.SPICE
        and by_yield[PlantYield.SUGAR] is CommodityKind.SUGAR
    )


async def test_a_goods_rule_price_moves_its_market_price(realm: Realm) -> None:
    plain = context(realm.session)
    dear = context(realm.session, rules=tuned(Rules(), goods={"books_base_price": 900}))
    assert price_of(dear, CommodityKind.BOOKS, 10, 10, 1.0) > price_of(plain, CommodityKind.BOOKS, 10, 10, 1.0)


async def test_the_fixup_seeds_new_goods_where_their_works_stand(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Kilnsby", population=20000)
    realm.session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.POTTERY, level=1, built_epoch=1))
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    assert await seed_new_goods(ctx, book) == 1
    assert await holding(realm.session, town.id, CommodityKind.POTTERY) > 0
    assert await seed_new_goods(ctx, book) == 0
