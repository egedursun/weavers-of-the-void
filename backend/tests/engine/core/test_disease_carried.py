from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, ImmunityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.disease.load import DiseaseLoads
from aerona.engine.environment.profile import climate_disease
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement

RULES = Rules()


async def ground_of(session: AsyncSession, region_id: int, world_id: int) -> RegionEnvironmentRow:
    ground = await session.scalar(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id == region_id))
    if ground is None:
        ground = RegionEnvironmentRow(
            entity_id=region_id,
            world_id=world_id,
            dominant_terrain=TerrainKind.PLAIN,
            elevation_mean=10,
            roughness=10,
            latitude=10,
            moisture=50,
            base_forest=10,
            forest_cover=10,
            base_wetland=10,
            wetland=10,
            river_class=RiverClass.RIVER,
            coast_kind=CoastKind.NONE,
            soil=next(iter(SoilKind)),
            soil_fertility=50,
            soil_base=50,
            temperature=50,
            temperature_band=TemperatureBand.TEMPERATE,
            rainfall=50,
            seasonality=10,
            disease_load=0,
            magic_density=0,
            defensibility=10,
            locked=[],
        )
        session.add(ground)
    return ground


async def test_the_ordinary_death_rates_carry_the_disease_of_a_warm_wet_lands_own_climate(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Reedmouth", world, world.regions[0])
    ground = await ground_of(session, world.regions[0].id, world.world.id)
    ground.temperature, ground.wetland = 90, 90
    ground.disease_load = round(climate_disease(RULES, temperature=90, wetland=90))
    await session.flush()
    loads = await DiseaseLoads.load(session, RULES)
    assert loads.carried(town) > RULES.demography.endemic_baseline / 100
    assert loads.lasting(town) - loads.carried(town) <= 0.01


async def test_folk_immune_to_an_endemic_sickness_bear_little_of_its_load(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Reedmouth", world, world.regions[0])
    ground = await ground_of(session, world.regions[0].id, world.world.id)
    ground.disease_load = 0
    ground.temperature, ground.wetland = 0, 0
    disease = await entity(session, "The Marsh Ague", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(EndemicDiseaseRow(region_entity_id=world.regions[0].id, disease_entity_id=disease.id, load=40, since_epoch=1))
    await session.flush()
    exposed = (await DiseaseLoads.load(session, RULES)).lasting(town)
    for band in AgeBand:
        session.add(ImmunityRow(community_entity_id=town.id, disease_entity_id=disease.id, age_band=band, immune_pct=100, since_epoch=1))
    await session.flush()
    guarded = (await DiseaseLoads.load(session, RULES)).lasting(town)
    assert exposed == 0.4
    assert guarded < exposed * (1 - RULES.epidemiology.immunity_strength_pct / 100) + 0.02
    assert (await DiseaseLoads.load(session, RULES)).of_region(world.regions[0].id) == 40


async def test_strains_of_one_sickness_burden_a_land_once_while_unrelated_sicknesses_add_up(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0].id
    ground = await ground_of(session, region, world.world.id)
    ground.disease_load, ground.temperature, ground.wetland = 0, 0, 0
    parent = await entity(session, "The Grey Fever", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    strain = await entity(session, "The Grey Fever, strain 2", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    other = await entity(session, "The Shaking Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    for disease, origin in ((parent, None), (strain, parent.id), (other, None)):
        session.add(
            DiseaseProfileRow(
                disease_entity_id=disease.id,
                primary_route=next(iter(Transmission)),
                virulence=30,
                lethality=30,
                chronic_rate=0,
                incubation=1,
                immunity_epochs=1,
                mutation_rate=10,
                stigma=0,
                cure_level=0,
                parent_disease_id=origin,
                locked=[],
            )
        )
    await session.flush()
    session.add(EndemicDiseaseRow(region_entity_id=region, disease_entity_id=parent.id, load=40, since_epoch=1))
    session.add(EndemicDiseaseRow(region_entity_id=region, disease_entity_id=strain.id, load=40, since_epoch=1))
    await session.flush()
    assert (await DiseaseLoads.load(session, RULES)).of_region(region) == 40
    session.add(EndemicDiseaseRow(region_entity_id=region, disease_entity_id=other.id, load=40, since_epoch=1))
    await session.flush()
    assert (await DiseaseLoads.load(session, RULES)).of_region(region) == 64
