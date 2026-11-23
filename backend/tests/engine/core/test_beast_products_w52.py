from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.beast_products import BEAST_PRODUCTS, BY_PRODUCT_NAME
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.ecology import YieldProduct
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.ranges import BEAST_FIRST_TRADED, beast_worth, first_beast_trade
from aerona.engine.ecology.w52_products import BEAST_PRODUCTS_FIXUP, backfill_beast_products, beast_category
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules

NEW = (YieldProduct.BLOOD, YieldProduct.ORGANS, YieldProduct.FAT, YieldProduct.SCENT, YieldProduct.HONEY, YieldProduct.WAX)


def test_every_product_has_its_worth_and_share_and_the_six_new_ones_are_named() -> None:
    assert set(BEAST_PRODUCTS) == set(YieldProduct)
    assert all(BY_PRODUCT_NAME[item.value] is item for item in NEW)
    rules = tuned_rules(beast_products={"honey_value": 300, "honey_yield": 50})
    assert beast_worth(rules, "honey") == 1.5
    assert beast_worth(rules, "a thing never named") == 1.0


async def test_a_town_first_bringing_a_product_to_market_is_told_once(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Hive Ford", world, world.regions[0])
    await first_beast_trade(ctx, town, YieldProduct.HONEY)
    await session.flush()
    await first_beast_trade(ctx, town, YieldProduct.HONEY)
    await first_beast_trade(ctx, town, None)
    await session.flush()
    told = await session.scalar(select(func.count(IncidentRow.id)).where(IncidentRow.kind == BEAST_FIRST_TRADED))
    assert told == 1


async def test_authored_beast_products_move_into_the_new_categories_once(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    kind = await entity(session, "Marsh Ox", EntityType.SPECIES, SpeciesStats(hp=30), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(SpeciesProfileRow(species_entity_id=kind.id))
    session.add(SpeciesProductRow(species_entity_id=kind.id, product="rendered fat", rate=2, locked=[]))
    session.add(SpeciesProductRow(species_entity_id=kind.id, product="horn dust", rate=1, locked=[]))
    await session.flush()
    assert beast_category("rendered fat") is YieldProduct.FAT and beast_category("horn dust") is None
    assert await backfill_beast_products(ctx) == 1
    products = set(await session.scalars(select(SpeciesProductRow.product).where(SpeciesProductRow.species_entity_id == kind.id)))
    assert products == {"fat", "horn dust"}
    assert await session.get(AppliedFixupRow, BEAST_PRODUCTS_FIXUP) is not None
    assert await backfill_beast_products(ctx) == 0
