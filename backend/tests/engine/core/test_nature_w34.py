from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.nature_lines import mortal_nature_lines
from aerona.agents.context.scope import load_scope
from aerona.catalog.senses import AGENTS, TRACKING
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cuisine import CommunityDishRow, DishRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.nature import FermentCultureRow, SenseProfileRow, SoilMicrobiotaRow, SpeciesRelationRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.ecology import Diet, DomesticationStage, SizeClass, SpeciesClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand, TerrainKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.nature import Dormancy, FermentKind, PlantDefence, SenseKind, SymbiosisKind, Thermoregulation
from aerona.domain.enums.region import DangerSource
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.environment.dangers import DangerScene
from aerona.engine.environment.dangers import _beasts as beasts_danger
from aerona.engine.nature.cover import defence_cover, grazing, passage, smothered
from aerona.engine.nature.islands import IslandTally, drifted_size, keep_islands, spared_kinds
from aerona.engine.nature.microbes import MicrobeTally, culture_lift, keep_microbes, microbe_factor
from aerona.engine.nature.seasons import activity, asleep, chilled
from aerona.engine.nature.senses import SenseTally, seed_senses, sense_score
from aerona.engine.nature.sleepers import SleeperTally, keep_sleepers, lair_factor, raid_factor
from aerona.engine.nature.symbiosis import SymbiosisBook, SymbiosisTally, form_relations, keep_symbiosis
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def surveyed(session: AsyncSession, epoch: int = 2, **namespaces: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    ctx = await manual_context(session, "living_nature", rules=tuned_rules(**namespaces))
    await environment_survey(ctx)
    return ctx


async def kind(session: AsyncSession, world: CoreWorld, name: str, region_id: int, abundance: int = 50, **profile: object) -> int:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=40, intelligence=30), world_id=world.world.id, location_id=region_id)
    session.add(SpeciesProfileRow(species_entity_id=species.id, locked=[], **profile))
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region_id, abundance=abundance, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    return species.id


async def land(session: AsyncSession, region_id: int) -> RegionEnvironmentRow:
    row = await session.get(RegionEnvironmentRow, region_id)
    assert row is not None
    return row


def test_seasons_set_sleep_activity_and_hunger() -> None:
    rules = tuned_rules()
    assert asleep(Dormancy.HIBERNATION, TemperatureBand.COLD) and not asleep(Dormancy.HIBERNATION, TemperatureBand.HOT)
    assert asleep(Dormancy.AESTIVATION, TemperatureBand.HOT) and not asleep(Dormancy.NONE, TemperatureBand.FROZEN)
    assert activity(rules, Thermoregulation.ECTOTHERM, TemperatureBand.COLD) == rules.thermoregulation.cold_pct / 100
    assert activity(rules, Thermoregulation.ENDOTHERM, TemperatureBand.FROZEN) == 1.0
    assert chilled(Thermoregulation.ENDOTHERM, TemperatureBand.COLD) and not chilled(Thermoregulation.ECTOTHERM, TemperatureBand.COLD)
    assert drifted_size(SizeClass.HUGE) is SizeClass.LARGE and drifted_size(SizeClass.TINY) is SizeClass.SMALL
    assert passage(rules, 1.0) < 1.0 and grazing(rules, 1.0) < 1.0 and smothered(rules, 0.5) < 1.0


def test_bonds_between_kinds_give_room_drain_hosts_and_shield_mimics() -> None:
    rules = tuned_rules()
    book = SymbiosisBook()
    for row in (
        SpeciesRelationRow(id=1, first_species_id=1, second_species_id=2, kind=SymbiosisKind.MUTUALISM, strength=100),
        SpeciesRelationRow(id=2, first_species_id=3, second_species_id=2, kind=SymbiosisKind.PARASITISM, strength=100),
        SpeciesRelationRow(id=3, first_species_id=4, second_species_id=5, kind=SymbiosisKind.MIMICRY, strength=100),
    ):
        book.relations.append(row)
        book.of_species[row.first_species_id].append(row)
        book.of_species[row.second_species_id].append(row)
    present = {1: 100, 2: 100, 3: 100, 4: 50, 5: 100}
    assert book.room(rules, 2, present) == 1 + rules.symbiosis.mutual_pct / 100
    assert book.drain(rules, 2, present) == rules.symbiosis.parasite_loss
    assert book.shield(rules, 4, present) == 1 - rules.symbiosis.mimic_shield_pct / 100


async def test_a_living_soil_recycles_faster_and_a_town_founds_and_trades_cultures(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, fermentation={"found_chance": 100, "trade_chance": 0})
    region = world.regions[0].id
    town = await settlement(session, "Brewby", world, world.regions[0])
    dish = DishRow(name="Sour Loaf", method=CookingMethod.BAKED, course=DishCourse.STAPLE, locked=[])
    session.add(dish)
    await session.flush()
    session.add(CommunityDishRow(community_entity_id=town.id, dish_id=dish.id, popularity=50, cooked=0, locked=[]))
    await session.flush()
    tally = MicrobeTally()
    await keep_microbes(ctx, tally)
    soil = await session.get(SoilMicrobiotaRow, region)
    assert soil is not None and tally.soils >= 1 and tally.founded == 1
    assert microbe_factor(ctx.rules, 100) > microbe_factor(ctx.rules, 50) == 1.0 > microbe_factor(ctx.rules, 0)
    culture = await session.scalar(select(FermentCultureRow).where(FermentCultureRow.holder_entity_id == town.id))
    assert culture is not None and culture.kind is FermentKind.STARTER
    assert await culture_lift(session, ctx.rules, town.id, CookingMethod.BAKED, DishCourse.STAPLE) > 1.0
    assert await culture_lift(session, ctx.rules, town.id, CookingMethod.ROASTED, DishCourse.STAPLE) == 1.0


async def test_kinds_that_share_a_land_form_bonds_and_plant_defences_cover_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, symbiosis={"form_chance": 100})
    region = world.regions[0].id
    moth = await kind(session, world, "Dusk Moth", region, species_class=SpeciesClass.ANIMAL, diet=Diet.HERBIVORE)
    bramble = await kind(session, world, "Hook Bramble", region, species_class=SpeciesClass.PLANT, diet=Diet.PHOTOSYNTHETIC)
    session.add(PlantProfileRow(species_entity_id=bramble, defence=PlantDefence.THORNS, defence_potency=100, locked=[]))
    await session.flush()
    tally = SymbiosisTally()
    await form_relations(ctx, tally)
    row = await session.scalar(select(SpeciesRelationRow))
    assert tally.formed == 1 and row is not None and row.kind is SymbiosisKind.MUTUALISM and row.first_species_id == moth
    assert (await defence_cover(session))[region][PlantDefence.THORNS] == 0.5


async def test_a_sleeping_kind_neither_raids_nor_resists_and_a_crowded_land_wakes_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, dormancy={"disturb_chance": 100, "disturb_population": 0, "disturb_aggression": 0})
    region = world.regions[0].id
    ground = await land(session, region)
    ground.temperature = 5
    await settlement(session, "Coldby", world, world.regions[0])
    bear = await kind(session, world, "Snow Bear", region, dormancy=Dormancy.HIBERNATION, aggression=80)
    monster = await session.get(EntityRow, bear)
    assert monster is not None
    assert await raid_factor(session, ctx.rules, ctx.epoch, monster) == 0.0
    assert await lair_factor(session, ctx.rules, ctx.epoch, monster) < 1.0
    tally = SleeperTally()
    await keep_sleepers(ctx, tally)
    assert tally.woken == 1
    assert await raid_factor(session, ctx.rules, ctx.epoch, monster) == ctx.rules.dormancy.woken_raid_pct / 100


async def test_senses_are_read_for_kinds_and_peoples_and_sharpen_detection(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    region = world.regions[0].id
    await kind(session, world, "Night Owl", region, nocturnal=True, migratory=True, diet=Diet.CARNIVORE)
    tally = SenseTally()
    await seed_senses(ctx, tally)
    assert tally.seeded >= 2
    owl = await session.scalar(select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.nocturnal.is_(True)))
    assert await session.get(SenseProfileRow, (owl, SenseKind.NIGHT_VISION)) is not None
    town = await settlement(session, "Scentby", world, world.regions[0])
    session.add(SenseProfileRow(holder_entity_id=world.people.id, sense=SenseKind.SMELL, acuity=100, locked=[]))
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    await session.flush()
    assert await sense_score(session, town.id, AGENTS) > 0.5
    assert await sense_score(session, town.id, TRACKING) > 0.0


async def test_island_kinds_drift_and_revered_endemics_are_spared(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, island_rule={"drift_epochs": 1})
    region = world.regions[0].id
    ground = await land(session, region)
    ground.dominant_terrain = TerrainKind.ISLAND
    giant = await kind(session, world, "Isle Ox", region, size_class=SizeClass.HUGE)
    town = await settlement(session, "Grove", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis.NATURE, value=90))
    await session.flush()
    tally = IslandTally()
    await keep_islands(ctx, tally)
    profile = await session.get(SpeciesProfileRow, giant)
    assert profile is not None and profile.size_class is SizeClass.LARGE and profile.endemic and tally.drifted >= 1
    assert (giant, region) in await spared_kinds(session, ctx.rules.island_rule.revered_value)


async def test_a_mortal_reads_its_people_s_senses_and_its_town_s_cultures(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Kiln", world, world.regions[0])
    me = await mortal(session, "Ysolde", world, town.id)
    await bond(session, me.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SenseProfileRow(holder_entity_id=world.people.id, sense=SenseKind.HEARING, acuity=80, locked=[]))
    session.add(FermentCultureRow(holder_entity_id=town.id, kind=FermentKind.YEAST, quality=40, since_epoch=0, locked=[]))
    await session.flush()
    lines = await mortal_nature_lines(await load_scope(session, tuned_rules()), me)
    assert any("hearing 80" in line for line in lines) and any("yeast culture" in line for line in lines)


async def test_a_new_kind_takes_its_sleep_blood_and_defence_from_its_maker_or_its_home(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    region = world.regions[0].id
    ground = await land(session, region)
    ground.seasonality = 90
    ground.temperature = 10
    await session.flush()
    serpent = await entity(session, "Fen Adder", EntityType.SPECIES, SpeciesStats(hp=20, intelligence=10), world_id=world.world.id, location_id=region)
    profile = await profile_of(ctx, serpent, SpeciesSpec(body_plan=BodyPlan.SERPENTINE, size_class=SizeClass.SMALL, diet=Diet.CARNIVORE))
    assert profile.thermoregulation is Thermoregulation.ECTOTHERM and profile.dormancy is Dormancy.HIBERNATION
    thorn = await entity(session, "Hook Thorn", EntityType.SPECIES, SpeciesStats(hp=5, intelligence=0), world_id=world.world.id, location_id=region)
    spec = SpeciesSpec(
        body_plan=BodyPlan.ARBOREAL, size_class=SizeClass.MEDIUM, diet=Diet.PHOTOSYNTHETIC, species_class=SpeciesClass.PLANT, plant_defence=PlantDefence.THORNS
    )
    grown = await profile_of(ctx, thorn, spec)
    await session.flush()
    plant = await session.get(PlantProfileRow, thorn.id)
    assert grown.dormancy is Dormancy.NONE and plant is not None and plant.defence is PlantDefence.THORNS
    assert plant.defence_potency == ctx.rules.plant_defences.default_potency


async def test_a_parasite_of_herds_raises_disease_and_a_mimic_is_feared_as_the_kind_it_copies(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0].id
    ctx = await surveyed(session, symbiosis={"vector_load": 10, "mimic_alarm_pct": 100})
    ground = await land(session, region)
    before = ground.disease_load
    host = await kind(session, world, "Woolback", region, stage=DomesticationStage.DOMESTICATED, aggression=0)
    tick = await kind(session, world, "Bloodmite", region, aggression=0)
    model = await kind(session, world, "Stingwing", region, aggression=90)
    mimic = await kind(session, world, "Falsewing", region, aggression=0)
    session.add_all(
        [
            SpeciesRelationRow(first_species_id=tick, second_species_id=host, kind=SymbiosisKind.PARASITISM, strength=100),
            SpeciesRelationRow(first_species_id=mimic, second_species_id=model, kind=SymbiosisKind.MIMICRY, strength=100),
        ]
    )
    await session.flush()
    await keep_symbiosis(ctx, SymbiosisTally())
    assert ground.disease_load == min(100, before + 10)
    scene = DangerScene(await RegionAtlas.load(session), {region: ground}, {region: world.regions[0]}, {})
    await beasts_danger(session, ctx.rules, scene)
    slot = scene.derived[region][DangerSource.BEASTS]
    alone = DangerScene(await RegionAtlas.load(session), {region: ground}, {region: world.regions[0]}, {})
    model_range = await session.get(SpeciesRangeRow, (model, region))
    assert model_range is not None
    model_range.abundance = 0
    await session.flush()
    await beasts_danger(session, ctx.rules, alone)
    assert slot.strength > alone.derived[region][DangerSource.BEASTS].strength
