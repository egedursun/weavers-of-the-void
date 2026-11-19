from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.plants import FORMS
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow, RegionCropRow
from aerona.db.tables.plants import PlantAnatomyRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Diet, GrowthCycle, SpeciesClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.plants import PlantForm
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.plants.bodies import PlantTally, keep_plants
from tests.engine.core.factories import CoreWorld, entity, surveyed


async def plant(session: AsyncSession, world: CoreWorld, cycle: GrowthCycle) -> int:
    kind = await entity(session, f"Silverbark {cycle.value}", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id)
    session.add(SpeciesProfileRow(species_entity_id=kind.id, species_class=SpeciesClass.PLANT, body_plan=BodyPlan.ARBOREAL, diet=Diet.PHOTOSYNTHETIC))
    session.add(PlantProfileRow(species_entity_id=kind.id, growth_cycle=cycle, locked=[]))
    await session.flush()
    return kind.id


def test_every_form_grows_parts() -> None:
    assert all(spec.parts for spec in FORMS.values())


async def test_a_tree_grows_its_body_and_its_parts_become_goods(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    kind = await plant(session, world, GrowthCycle.TREE)
    await keep_plants(ctx, PlantTally())
    anatomy = await session.get(PlantAnatomyRow, kind)
    assert anatomy is not None and anatomy.form is PlantForm.TREE and anatomy.first_harvest_years == ctx.rules.plants.years_to_first_harvest_tree
    products = set(await session.scalars(select(SpeciesProductRow.product).where(SpeciesProductRow.species_entity_id == kind)))
    assert {"wood", "fruit"} <= products


async def test_a_fire_burns_herb_crops_but_spares_trees(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    herb = await plant(session, world, GrowthCycle.ANNUAL)
    tree = await plant(session, world, GrowthCycle.TREE)
    region = world.regions[0].id
    session.add_all(
        [
            RegionCropRow(region_entity_id=region, plant_entity_id=herb, share=50, locked=[]),
            RegionCropRow(region_entity_id=region, plant_entity_id=tree, share=50, locked=[]),
        ]
    )
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, region)
    assert land is not None
    land.burned_epoch = ctx.epoch
    await session.flush()
    await keep_plants(ctx, PlantTally())
    burned = await session.get(RegionCropRow, (region, herb))
    spared = await session.get(RegionCropRow, (region, tree))
    assert burned is not None and burned.share < 50
    assert spared is not None and spared.share == 50
