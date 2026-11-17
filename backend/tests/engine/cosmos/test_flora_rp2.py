import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.flora import PRODUCT_BY_NAME
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import HerdRow, SpeciesHostRow, SpeciesProductRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesUseRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import CropPestRow, PlantProfileRow, RegionCropRow, WorldBiochemistryRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.ecology import AnimalRole, Biochemistry, Cultivation, Diet, DomesticationStage, GrowthCycle, PlantYield, SizeClass, SpeciesClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind, WeatherEffect, WeatherKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.world import Atmosphere, WorldType
from aerona.domain.models.entity_stats import DiseaseStats, MortalStats, PeopleStats, SettlementStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.biochemistry import can_live_on, seed_world_life, tolerated
from aerona.engine.ecology.domestication import carry_herds
from aerona.engine.ecology.flora import (
    CropBook,
    CropField,
    CropYear,
    blight,
    breed_cultivars,
    crop_year,
    flora_backfill,
    gather_wild,
    link_pests,
    rebalance,
    split_fields,
)
from aerona.engine.ecology.flora_control import edit_plant, set_crop, set_crop_pest, set_world_life
from aerona.engine.ecology.pests import crop_loss
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.economy.stocks import GoodsLedger, holding
from aerona.engine.environment.weather import Weather
from aerona.engine.industry.stores import pest_hunters, vermin_in
from aerona.engine.intrigue.schemes import poison_well
from aerona.engine.phases.creatures import introduce_species
from aerona.engine.phases.environment import year_harvest
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_world, tick, tuned


async def land(session: AsyncSession, region_id: int, world_id: int, *, temperature: int = 55, moisture: int = 60, soil: int = 60) -> RegionEnvironmentRow:
    row = RegionEnvironmentRow(
        entity_id=region_id,
        world_id=world_id,
        dominant_terrain=TerrainKind.PLAIN,
        elevation_mean=20,
        roughness=10,
        latitude=40,
        moisture=moisture,
        base_forest=40,
        forest_cover=40,
        base_wetland=10,
        wetland=10,
        river_class=RiverClass.NONE,
        coast_kind=CoastKind.NONE,
        soil=SoilKind.LOAM,
        soil_fertility=soil,
        soil_base=soil,
        temperature=temperature,
        temperature_band=TemperatureBand.TEMPERATE,
        rainfall=50,
        seasonality=10,
        disease_load=0,
        magic_density=0,
        defensibility=20,
        harvest_pct=100,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return row


async def plant(ctx: TickContext, cosmos: Cosmos, name: str, region_id: int, *yields: PlantYield, cycle: GrowthCycle = GrowthCycle.ANNUAL) -> EntityRow:
    species = await make_entity(ctx.session, name, EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region_id)
    await profile_of(ctx, species, SpeciesSpec(species_class=SpeciesClass.PLANT, growth_cycle=cycle, plant_yields=yields))
    return species


async def farmers(session: AsyncSession, cosmos: Cosmos, region_id: int, level: int) -> EntityRow:
    people = await make_entity(session, "Furrow Hold", EntityType.SETTLEMENT, SettlementStats(population=900), world_id=cosmos.home.id, location_id=region_id)
    session.add(HolderLevelRow(holder_entity_id=people.id, branch=KnowledgeBranch.AGRICULTURE, level=level))
    await session.flush()
    return people


async def test_a_plant_grows_its_own_profile_and_harvest_never_meat(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Downs", cosmos.home.id)
    crop = await plant(ctx, cosmos, "Field Barley", region.id, PlantYield.GRAIN, PlantYield.BREW_BASE)
    profile = await ctx.session.get(SpeciesProfileRow, crop.id)
    grows = await ctx.session.get(PlantProfileRow, crop.id)
    assert profile is not None and profile.species_class is SpeciesClass.PLANT and profile.diet is Diet.PHOTOSYNTHETIC
    assert grows is not None and grows.growth_cycle is GrowthCycle.ANNUAL and grows.cultivation is Cultivation.WILD
    products = {
        row.product: row.commodity for row in await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == crop.id))
    }
    assert products == {"grain": CommodityKind.GRAIN, "brew_base": CommodityKind.BREW_BASE}
    assert not list(await ctx.session.scalars(select(SpeciesUseRow).where(SpeciesUseRow.species_entity_id == crop.id)))
    tree = await make_entity(ctx.session, "Old Oak", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    shaped = await profile_of(ctx, tree, SpeciesSpec(body_plan=BodyPlan.ARBOREAL, size_class=SizeClass.HUGE))
    assert shaped.species_class is SpeciesClass.PLANT
    oak = await ctx.session.get(PlantProfileRow, tree.id)
    assert oak is not None and oak.growth_cycle is GrowthCycle.TREE
    made = set(await ctx.session.scalars(select(SpeciesProductRow.product).where(SpeciesProductRow.species_entity_id == tree.id)))
    assert made == {"timber", "fruit"}


async def test_crops_that_suit_a_land_give_a_full_harvest_and_ill_suited_ones_do_not(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    warm = await make_region(ctx.session, "Warm Vale", cosmos.home.id)
    cold = await make_region(ctx.session, "Cold Fell", cosmos.home.id)
    await land(ctx.session, warm.id, cosmos.home.id, temperature=55)
    await land(ctx.session, cold.id, cosmos.home.id, temperature=0, soil=5)
    crop = await plant(ctx, cosmos, "Vale Wheat", warm.id, PlantYield.GRAIN, PlantYield.FIBRE)
    profile = await ctx.session.get(SpeciesProfileRow, crop.id)
    assert profile is not None
    profile.temperature_min, profile.temperature_max, profile.water_need = 40, 70, 60
    for region in (warm, cold):
        ctx.session.add(RegionCropRow(region_entity_id=region.id, plant_entity_id=crop.id, share=100, since_epoch=1, locked=[]))
    await ctx.session.flush()
    book = await CropBook.load(ctx.session, rules)
    assert book.fit(crop.id, warm.id) == pytest.approx(1.0)
    assert book.factor(warm.id) == pytest.approx(1.0)
    assert book.factor(cold.id) == pytest.approx(1 - rules.flora.crop_weight_pct / 100)
    assert book.factor(12345) == 1.0
    full = year_harvest(rules, growth=100, weather_growth=0, farming=0.0, agriculture=1.0, planned=False, blight=0, soil=60, crops=book.factor(warm.id))
    poor = year_harvest(rules, growth=100, weather_growth=0, farming=0.0, agriculture=1.0, planned=False, blight=0, soil=60, crops=book.factor(cold.id))
    assert poor < full
    goods = split_fields(rules, 100.0, book.fields(warm.id))
    assert goods[CommodityKind.GRAIN] == pytest.approx(100.0)
    assert goods[CommodityKind.FIBRE] == pytest.approx(100 * rules.flora.side_yield_pct / 100)
    dye = split_fields(rules, 50.0, [CropField(crop.id, 50, ((PRODUCT_BY_NAME["fibre"], 2),))])
    assert dye[CommodityKind.FIBRE] == pytest.approx(50 * 2 * rules.flora.sole_yield_pct / 100)


async def test_farmers_gather_then_sow_a_wild_plant_and_a_master_farmer_breeds_a_cultivar(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Loam Reach", cosmos.home.id)
    await land(ctx.session, region.id, cosmos.home.id)
    folk = await farmers(ctx.session, cosmos, region.id, level=2)
    crop = await plant(ctx, cosmos, "Reach Millet", region.id, PlantYield.GRAIN)
    ctx.session.add(SpeciesRangeRow(species_entity_id=crop.id, region_entity_id=region.id, abundance=40, since_epoch=0, locked=[]))
    await ctx.session.flush()
    eager = tick(ctx.session, tuned(rules, "flora", gather_pct=100, cultivate_pct=100, cultivar_pct=100, cultivar_epochs=0, cultivar_skill=10))
    atlas = await RegionAtlas.load(ctx.session)
    book = await CropBook.load(ctx.session, eager.rules)
    assert (await gather_wild(eager, book, atlas))["plants_gathered"] == 1
    assert book.plants[crop.id].cultivation is Cultivation.GATHERED
    assert (await gather_wild(eager, book, atlas))["plants_sown"] == 1
    assert book.plants[crop.id].cultivation is Cultivation.CULTIVATED
    assert await ctx.session.get(RegionCropRow, (region.id, crop.id)) is not None
    farmer = await make_entity(ctx.session, "Tilla", EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=folk.id)
    ctx.session.add(SkillRow(holder_node_id=farmer.id, skill=SkillKind.FORAGING, level=60, peak=60, last_used_epoch=1, source=SkillSource.PRACTICE))
    await ctx.session.flush()
    assert await breed_cultivars(eager, book, atlas) == 1
    sown = list(await ctx.session.scalars(select(RegionCropRow).where(RegionCropRow.region_entity_id == region.id)))
    assert len(sown) == 1 and sown[0].plant_entity_id != crop.id
    bred = await ctx.session.get(PlantProfileRow, sown[0].plant_entity_id)
    assert bred is not None and bred.cultivation is Cultivation.CULTIVAR and bred.cultivar_of_id == crop.id
    assert bred.soil_need == max(0, rules.flora.soil_need - rules.flora.cultivar_soil)
    rate = await ctx.session.get(SpeciesProductRow, (sown[0].plant_entity_id, "grain"))
    assert rate is not None and rate.rate > 2


async def test_shares_drift_towards_the_crops_that_suit_the_land_and_held_shares_stay(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Mixed Field", cosmos.home.id)
    await land(ctx.session, region.id, cosmos.home.id, temperature=55)
    good = await plant(ctx, cosmos, "Good Oat", region.id, PlantYield.GRAIN)
    poor = await plant(ctx, cosmos, "Poor Rye", region.id, PlantYield.GRAIN)
    held = await plant(ctx, cosmos, "Held Flax", region.id, PlantYield.FIBRE)
    for species, low, high in ((good, 40, 70), (poor, 85, 100), (held, 40, 70)):
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        assert profile is not None
        profile.temperature_min, profile.temperature_max, profile.water_need = low, high, 60
    ctx.session.add_all(
        [
            RegionCropRow(region_entity_id=region.id, plant_entity_id=good.id, share=30, since_epoch=1, locked=[]),
            RegionCropRow(region_entity_id=region.id, plant_entity_id=poor.id, share=50, since_epoch=1, locked=[]),
            RegionCropRow(region_entity_id=region.id, plant_entity_id=held.id, share=20, since_epoch=1, locked=["share"]),
        ]
    )
    await ctx.session.flush()
    book = await CropBook.load(ctx.session, tuned(rules, "flora", share_drift=100))
    rebalance(book.rules, book, region.id)
    shares = {row.plant_entity_id: row.share for row in book.crops[region.id]}
    assert shares[held.id] == 20 and shares[good.id] > shares[poor.id] and shares[good.id] + shares[poor.id] <= 80


async def test_pests_take_to_crops_and_only_strip_the_harvest_of_their_hosts(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Pest Flats", cosmos.home.id)
    await land(ctx.session, region.id, cosmos.home.id)
    crop = await plant(ctx, cosmos, "Flat Bean", region.id, PlantYield.GRAIN)
    pest = await make_entity(ctx.session, "Field Gnawer", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add(EntityTraitRow(entity_id=pest.id, trait=CreatureTrait.CROP_PEST))
    await profile_of(ctx, pest, SpeciesSpec(size_class=SizeClass.TINY, diet=Diet.HERBIVORE))
    ctx.session.add(RegionCropRow(region_entity_id=region.id, plant_entity_id=crop.id, share=40, since_epoch=1, locked=[]))
    ctx.session.add(SpeciesRangeRow(species_entity_id=pest.id, region_entity_id=region.id, abundance=100, since_epoch=0, locked=[]))
    await ctx.session.flush()
    vermin = await ctx.session.get(SpeciesProfileRow, pest.id)
    assert vermin is not None and vermin.species_class is SpeciesClass.VERMIN
    assert await vermin_in(ctx, region.id)
    legacy = await crop_loss(ctx, pest.id, region.id, 1.0)
    assert legacy == rules.pests.harvest_loss
    eager = tick(ctx.session, tuned(rules, "flora", pest_link_pct=100))
    assert await link_pests(eager, await CropBook.load(ctx.session, eager.rules)) == 1
    assert await ctx.session.get(CropPestRow, (crop.id, pest.id)) is not None
    assert await crop_loss(ctx, pest.id, region.id, 1.0) == pytest.approx(rules.flora.pest_loss * 0.4)


async def test_a_raging_sickness_of_a_crop_blights_its_fields(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Blight Moor", cosmos.home.id)
    env = await land(ctx.session, region.id, cosmos.home.id)
    crop = await plant(ctx, cosmos, "Moor Root", region.id, PlantYield.TUBER)
    sickness = await make_entity(ctx.session, "Root Rot", EntityType.DISEASE, DiseaseStats(), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add(SpeciesHostRow(species_entity_id=crop.id, disease_entity_id=sickness.id, immune=False, locked=[]))
    ctx.session.add(
        OutbreakRow(
            disease_entity_id=sickness.id, region_entity_id=region.id, path=SpreadPath.ORIGIN, status=OutbreakStatus.ACTIVE, severity=50, started_epoch=1
        )
    )
    ctx.session.add(RegionCropRow(region_entity_id=region.id, plant_entity_id=crop.id, share=50, since_epoch=1, locked=[]))
    await ctx.session.flush()
    book = await CropBook.load(ctx.session, rules)
    assert await blight(ctx, book) == 1
    assert env.harvest_pct == 100 - round(rules.flora.blight_loss * 0.5)


async def test_worlds_bear_only_some_kinds_of_life_and_the_gates_follow(ctx: TickContext, cosmos: Cosmos) -> None:
    barren = await make_world(ctx.session, "Glass Moon", WorldType.CRYSTAL)
    barren.atmosphere = Atmosphere.NONE
    await ctx.session.flush()
    assert await tolerated(ctx.session, barren.id) == (Biochemistry.SILICON, Biochemistry.CRYSTAL)
    assert await seed_world_life(ctx.session) >= 2
    assert await seed_world_life(ctx.session) == 0
    rows = set(await ctx.session.scalars(select(WorldBiochemistryRow.biochemistry).where(WorldBiochemistryRow.world_id == barren.id)))
    assert rows == {Biochemistry.SILICON, Biochemistry.CRYSTAL}
    home = await make_region(ctx.session, "Home Meadow", cosmos.home.id)
    far = await make_region(ctx.session, "Glass Plain", barren.id)
    grazer = await make_entity(ctx.session, "Meadow Grazer", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=home.id)
    await profile_of(ctx, grazer, SpeciesSpec(diet=Diet.HERBIVORE))
    wisp = await make_entity(ctx.session, "Drifting Wisp", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=home.id)
    await profile_of(ctx, wisp, SpeciesSpec(biochemistry=Biochemistry.SPIRIT))
    assert not await can_live_on(ctx.session, grazer.id, barren.id)
    assert await can_live_on(ctx.session, wisp.id, barren.id)
    with pytest.raises(ValidationFailedError):
        await introduce_species(ctx.session, ctx.rules, grazer.id, far.id)
    native = await make_entity(ctx.session, "Glass Crawler", EntityType.SPECIES, SpeciesStats(), world_id=barren.id, location_id=far.id)
    assert (await profile_of(ctx, native)).biochemistry is Biochemistry.SILICON
    village = await make_entity(ctx.session, "Meadow Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id, location_id=home.id)
    colony = await make_entity(ctx.session, "Glass Hold", EntityType.SETTLEMENT, SettlementStats(population=50), world_id=barren.id, location_id=far.id)
    for kind in (grazer, wisp):
        ctx.session.add(
            HerdRow(community_entity_id=village.id, species_entity_id=kind.id, head=50, stage=DomesticationStage.HERDED, since_epoch=1, fed_epochs=0, locked=[])
        )
    await ctx.session.flush()
    assert await carry_herds(ctx, village.id, colony) == (1, 1)
    assert await ctx.session.get(HerdRow, (colony.id, wisp.id)) is not None
    assert await ctx.session.get(HerdRow, (colony.id, grazer.id)) is None
    assert Biochemistry.CARBON_WATER in await set_world_life(ctx, barren.id, Biochemistry.CARBON_WATER, present=True)
    assert await can_live_on(ctx.session, grazer.id, barren.id)
    await set_world_life(ctx, barren.id, Biochemistry.CARBON_WATER, present=False)
    assert not await can_live_on(ctx.session, grazer.id, barren.id)


async def test_the_backfill_gives_old_kinds_their_class_life_and_herd_goods(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Old Wood", cosmos.home.id)
    tree = await make_entity(ctx.session, "Elder Tree", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    sheep = await make_entity(ctx.session, "Hill Sheep", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    mouser = await make_entity(ctx.session, "Barn Mouser", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add_all(
        [
            SpeciesProfileRow(species_entity_id=tree.id, body_plan=BodyPlan.ARBOREAL, diet=Diet.PHOTOSYNTHETIC, locked=[]),
            SpeciesProfileRow(species_entity_id=sheep.id, diet=Diet.HERBIVORE, locked=[]),
            SpeciesProfileRow(species_entity_id=mouser.id, diet=Diet.CARNIVORE, size_class=SizeClass.SMALL, locked=[]),
            SpeciesProductRow(species_entity_id=tree.id, product="meat", commodity=CommodityKind.LIVESTOCK, rate=2),
            SpeciesProductRow(species_entity_id=sheep.id, product="wool", commodity=CommodityKind.CLOTH, rate=1),
            SpeciesProductRow(species_entity_id=sheep.id, product="milk", commodity=CommodityKind.LIVESTOCK, rate=1),
            SpeciesUseRow(species_entity_id=tree.id, use=AnimalRole.MEAT),
        ]
    )
    await ctx.session.flush()
    counts = await flora_backfill(ctx)
    assert counts["plants"] == 1 and counts["herd_goods"] == 2 and counts["pest_hunters"] == 1
    profile = await ctx.session.get(SpeciesProfileRow, tree.id)
    assert profile is not None and profile.species_class is SpeciesClass.PLANT
    assert await ctx.session.get(SpeciesProductRow, (tree.id, "meat")) is None
    assert await ctx.session.get(SpeciesUseRow, (tree.id, AnimalRole.MEAT)) is None
    wool = await ctx.session.get(SpeciesProductRow, (sheep.id, "wool"))
    assert wool is not None and wool.commodity is CommodityKind.WOOL
    assert await ctx.session.get(AppliedFixupRow, "flora.typed_flora") is not None
    assert (await flora_backfill(ctx))["plants"] == 0
    village = await make_entity(ctx.session, "Barn Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add(
        HerdRow(community_entity_id=village.id, species_entity_id=mouser.id, head=10, stage=DomesticationStage.HERDED, since_epoch=1, fed_epochs=0, locked=[])
    )
    await ctx.session.flush()
    assert await pest_hunters(ctx, village.id)


async def test_the_god_shapes_plants_crops_pests_and_held_shares(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "God Field", cosmos.home.id)
    await land(ctx.session, region.id, cosmos.home.id)
    crop = await plant(ctx, cosmos, "God Lentil", region.id, PlantYield.GRAIN)
    pest = await make_entity(ctx.session, "Lentil Moth", EntityType.SPECIES, SpeciesStats(), world_id=cosmos.home.id, location_id=region.id)
    await profile_of(ctx, pest)
    row = await edit_plant(ctx, crop.id, {"cultivation": "cultivated", "soil_need": 10}, release=[])
    assert row.cultivation is Cultivation.CULTIVATED and row.soil_need == 10 and set(row.locked) == {"cultivation", "soil_need"}
    with pytest.raises(ValidationFailedError):
        await edit_plant(ctx, pest.id, {"soil_need": 5}, release=[])
    sown = await set_crop(ctx, region.id, crop.id, 70, hold=True, release=[])
    assert sown.share == 70 and "share" in sown.locked
    freed = await set_crop(ctx, region.id, crop.id, None, hold=False, release=["share"])
    assert freed.share == 70 and "share" not in freed.locked
    assert await set_crop_pest(ctx, crop.id, pest.id, present=True) is not None
    assert await set_crop_pest(ctx, crop.id, pest.id, present=False) is None


async def test_a_poisoned_well_kills_more_when_the_schemer_brings_poison_from_stores(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Well Vale", cosmos.home.id)
    plotters = await make_entity(ctx.session, "Plotters", EntityType.PEOPLE, PeopleStats(population=1000), world_id=cosmos.home.id, location_id=region.id)
    first = await make_entity(ctx.session, "First Town", EntityType.PEOPLE, PeopleStats(population=1000), world_id=cosmos.home.id, location_id=region.id)
    second = await make_entity(ctx.session, "Second Town", EntityType.PEOPLE, PeopleStats(population=1000), world_id=cosmos.home.id, location_id=region.id)
    scheme = SchemeRow()
    assert "brought from stores" not in await poison_well(ctx, scheme, plotters, first)
    await GoodsLedger(ctx.session, ctx.epoch).add(plotters.id, CommodityKind.POISON, 2, GoodsFlow.PRODUCTION)
    assert "brought from stores" in await poison_well(ctx, scheme, plotters, second)
    assert await holding(ctx.session, plotters.id, CommodityKind.POISON) == 1
    assert (second.stats.population or 0) < (first.stats.population or 0)


async def test_a_cold_or_wet_year_hurts_a_tender_crop_and_spares_a_hardy_one(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    vale = await make_region(ctx.session, "Frost Vale", cosmos.home.id)
    await land(ctx.session, vale.id, cosmos.home.id, temperature=50, moisture=40)
    tender = await plant(ctx, cosmos, "Sun Melon", vale.id, PlantYield.FRUIT)
    hardy = await plant(ctx, cosmos, "Frost Rye", vale.id, PlantYield.GRAIN)
    for crop, low, high in ((tender, 45, 80), (hardy, 5, 60)):
        profile = await ctx.session.get(SpeciesProfileRow, crop.id)
        assert profile is not None
        profile.temperature_min, profile.temperature_max, profile.water_need = low, high, 40
    ctx.session.add(RegionCropRow(region_entity_id=vale.id, plant_entity_id=tender.id, share=100, since_epoch=1, locked=[]))
    await ctx.session.flush()
    book = await CropBook.load(ctx.session, rules)
    blizzard = Weather(WeatherKind.BLIZZARD, "Blizzard", {**dict.fromkeys(WeatherEffect, 0), WeatherEffect.COLD: 100})
    cold = crop_year(rules, blizzard)
    assert cold.degrees == -rules.flora.weather_degrees and cold.moisture == 0
    assert book.fit(tender.id, vale.id, cold) < book.fit(tender.id, vale.id)
    assert book.fit(hardy.id, vale.id, cold) == pytest.approx(book.fit(hardy.id, vale.id))
    assert book.factor(vale.id, cold) < book.factor(vale.id)
    assert book.fit(hardy.id, vale.id, CropYear(moisture=60)) < book.fit(hardy.id, vale.id)


async def test_a_yield_the_god_names_freely_still_fills_the_fields_by_its_goods(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    vale = await make_region(ctx.session, "Barley Vale", cosmos.home.id)
    await land(ctx.session, vale.id, cosmos.home.id)
    crop = await plant(ctx, cosmos, "Vale Barley", vale.id, PlantYield.GRAIN)
    for item in list(await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == crop.id))):
        await ctx.session.delete(item)
    ctx.session.add(SpeciesProductRow(species_entity_id=crop.id, product="barley", commodity=CommodityKind.GRAIN, rate=2))
    ctx.session.add(SpeciesProductRow(species_entity_id=crop.id, product="song", commodity=None, rate=1))
    ctx.session.add(RegionCropRow(region_entity_id=vale.id, plant_entity_id=crop.id, share=100, since_epoch=1, locked=[]))
    await ctx.session.flush()
    book = await CropBook.load(ctx.session, rules)
    fields = book.fields(vale.id)
    assert [(product.commodity, rate) for crop_field in fields for product, rate in crop_field.products] == [(CommodityKind.GRAIN, 2)]
    assert split_fields(rules, 10.0, fields)[CommodityKind.GRAIN] == pytest.approx(10.0)
