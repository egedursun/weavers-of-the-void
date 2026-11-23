from types import SimpleNamespace
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.flora import PLANT_PRODUCTS
from aerona.db.tables.ecology import HerdRow, SpeciesProductRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.plants import PlantAnatomyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import DomesticationStage, PlantYield
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.plants import PlantForm, PlantPart, PlantReproduction
from aerona.engine.customs.intoxicants import grows_stimulant
from aerona.engine.ecology.flora import CropField, product_worth
from aerona.engine.ecology.living_ways import feed_herds, keep_living_ways, load, tap_resin
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.household import first_harvests
from aerona.engine.economy.stocks import goods_of, holdings
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, settlement, tuned_rules
from tests.engine.core.living_kinds import kind, land, range_of, told

RULES = Rules()


async def plant(session: AsyncSession, world: CoreWorld, name: str, region: EntityRow, abundance: int, *, form: PlantForm) -> EntityRow:
    species = await kind(session, world, name, region, abundance)
    session.add(PlantAnatomyRow(species_entity_id=species.id, form=form, reproduction=PlantReproduction.WIND_SEED, locked=[]))
    await session.flush()
    return species


def test_thirteen_forms_thirteen_parts_and_sixteen_products_each_with_its_worth() -> None:
    assert len(PlantForm) == 13 and len(PlantPart) == 13 and len(PlantYield) == 16
    assert set(PLANT_PRODUCTS) == set(PlantYield)
    assert product_worth(RULES, PLANT_PRODUCTS[PlantYield.SPICE]) > product_worth(RULES, PLANT_PRODUCTS[PlantYield.GRAIN])
    assert product_worth(RULES, PLANT_PRODUCTS[PlantYield.FODDER]) < 1.0


async def test_an_epiphyte_thins_where_the_forest_is_gone_and_a_parasite_weakens_the_harvest(session: AsyncSession, world: CoreWorld) -> None:
    bare, fields = world.regions[0], world.regions[1]
    await land(session, world, bare, forest_cover=5)
    ground = await land(session, world, fields, harvest_pct=100)
    hanging = await plant(session, world, "Branch Orchid", bare, 50, form=PlantForm.EPIPHYTE)
    await plant(session, world, "Root Strangler", fields, 100, form=PlantForm.PARASITIC)
    ctx = await manual_context(session, "ecology", tuned_rules(plants_depth={"epiphyte_host_need": 40, "parasitic_host_harm": 20}))
    await keep_living_ways(ctx, set())
    assert (await range_of(session, hanging, bare)).abundance == 46
    assert ground.harvest_pct == 80 and await told(session, "life.host_weakened")


async def test_resin_plants_are_tapped_for_incense_at_a_cost_to_their_numbers(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[1]
    town = await settlement(session, "Pitch Town", world, region)
    tree = await plant(session, world, "Weeping Pine", region, 100, form=PlantForm.TREE)
    ctx = await manual_context(session, "ecology", tuned_rules(plants_depth={"resin_tap_yield": 12, "resin_tap_harm": 5}))
    await tap_resin(ctx, await load(ctx), {tree.id})
    await session.flush()
    assert (await holdings(session, town.id)).get(CommodityKind.INCENSE, 0) == 11
    assert (await range_of(session, tree, region)).abundance == 95 and await told(session, "life.resin_tapped")


async def test_fodder_carries_a_herd_through_the_lean_season(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    town = await settlement(session, "Byre Town", world, region)
    cattle = await kind(session, world, "Byre Ox", region, 30)
    herd = HerdRow(community_entity_id=town.id, species_entity_id=cattle.id, head=100, stage=DomesticationStage.DOMESTICATED, locked=[])
    session.add(herd)
    await session.flush()
    ctx = await manual_context(session, "ecology", tuned_rules(plant_products={"fodder_herd_gain": 50, "fodder_per_head": 10}))
    await goods_of(session, ctx.epoch).add(town.id, CommodityKind.FODDER, 10, GoodsFlow.HARVEST)
    await feed_herds(ctx)
    assert herd.head == 105


async def test_a_people_whose_lands_grow_a_stimulant_knows_it_and_its_first_harvest_is_told(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    town = await settlement(session, "Leaf Town", world, region)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    shrub = await plant(session, world, "Waking Leaf", region, 60, form=PlantForm.SHRUB)
    ctx = await manual_context(session, "economy")
    assert not await grows_stimulant(ctx, world.people.id)
    session.add(SpeciesProductRow(species_entity_id=shrub.id, product=PlantYield.STIMULANT.value, commodity=CommodityKind.LUXURIES, rate=1, locked=[]))
    await session.flush()
    assert await grows_stimulant(ctx, world.people.id)
    field = CropField(shrub.id, 50, ((PLANT_PRODUCTS[PlantYield.STIMULANT], 10),))
    book = SimpleNamespace(
        ground=SimpleNamespace(region_of=lambda _community: SimpleNamespace(entity_id=region.id)), crops=SimpleNamespace(fields=lambda _region: [field])
    )
    await first_harvests(ctx, cast(EconomyBook, book), town)
    assert await told(session, "trade.product_first_traded")
