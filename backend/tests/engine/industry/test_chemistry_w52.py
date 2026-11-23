from aerona.catalog.goods_tables import RECIPES
from aerona.db.tables.crafts import ChemicalWorksRow
from aerona.domain.enums.crafts import ChemicalProduct
from aerona.engine.crafts.works import etched, glazed, inked, preserved
from tests.engine.society.factories import Realm, context, settlement

NEW = (ChemicalProduct.INK, ChemicalProduct.GLAZE, ChemicalProduct.PRESERVATIVE, ChemicalProduct.ACID)


def test_twelve_chemical_products_each_with_a_recipe() -> None:
    assert len(ChemicalProduct) == 12 and all(product in RECIPES for product in NEW)


async def test_ink_glaze_preservatives_and_acids_feed_their_crafts(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Vatsby")
    assert await inked(realm.session, ctx.rules, town.id) == 1.0 and await glazed(realm.session, ctx.rules, town.id) == 0
    for product in NEW:
        realm.session.add(ChemicalWorksRow(settlement_entity_id=town.id, product=product, output=100, founded_epoch=1, locked=[]))
    await realm.session.flush()
    assert await inked(realm.session, ctx.rules, town.id) > 1.0
    assert await glazed(realm.session, ctx.rules, town.id) == ctx.rules.chemistry.glaze_quality
    assert await preserved(realm.session, ctx.rules, town.id) < 1.0
    assert await etched(realm.session, ctx.rules, town.id) > 1.0
