from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import STAGE_COVER, climax_stage, keystone_of, next_stage, trophic_level
from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseCureRow, DiseaseProfileRow, OutbreakRow, QuarantineRow
from aerona.db.tables.ecology import HerdRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import CureResearchRow, EcosystemServiceRow, LineageMarkRow, SpeciesTraitRow, TrophicLevelRow, WorldCycleRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import ClimateAffinity, DiseaseTarget, DiseaseVector, SpreadPath
from aerona.domain.enums.ecology import Diet, DomesticationStage, SizeClass
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, TemperatureBand
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse, SuccessionStage, TrophicLevel
from aerona.domain.enums.happening import LandAct
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import DiseaseStats, SpeciesStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import CycleTally, carbon_flux, turn_cycles
from aerona.engine.cosmos.planetary import move_carbon
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.evolution import take_symptom
from aerona.engine.disease.outbreaks import answered, resisted, tolerance_fit
from aerona.engine.disease.research import ResearchTally, found_cure
from aerona.engine.disease.responses import leaning, resentment, take_up
from aerona.engine.disease.stigma import expel_sick
from aerona.engine.ecology.evolution import EvolutionTally, apart, cold_reach, escape, evolve_traits, fecund, inherit_traits, wary
from aerona.engine.ecology.evolution_control import set_trait, shape_land
from aerona.engine.ecology.feral import FeralTally, release_herd, run_wild
from aerona.engine.ecology.keystones import KeystoneTally, keep_services, pollination
from aerona.engine.ecology.lineages import LineageTally, mark, mark_lineages
from aerona.engine.ecology.niches import NicheTally, compete
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.ecology.trophic import TrophicTally, balance_food_chain
from aerona.engine.environment.succession import SuccessionTally, burn_back, grow_lands
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.services.integrity.evolution_links import mend_evolution_links
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def surveyed(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    ctx = await manual_context(session, "evolution", rules=tuned_rules(**namespaces))
    await environment_survey(ctx)
    return ctx


async def beast_kind(session: AsyncSession, world: CoreWorld, name: str, region_id: int, abundance: int = 50) -> EntityRow:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=40, intelligence=30), world_id=world.world.id, location_id=region_id)
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region_id, abundance=abundance, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    return species


def test_the_catalogue_reads_stages_roles_and_levels() -> None:
    assert climax_stage(70, 10, 50) is SuccessionStage.OLD_FOREST
    assert climax_stage(10, 50, 50) is SuccessionStage.MARSH
    assert climax_stage(0, 0, 5) is SuccessionStage.BARE
    assert next_stage(SuccessionStage.GRASSLAND, wet=False) is SuccessionStage.SHRUBLAND
    assert next_stage(SuccessionStage.GRASSLAND, wet=True) is SuccessionStage.MARSH
    assert next_stage(SuccessionStage.OLD_FOREST, wet=False) is None
    assert keystone_of(BodyPlan.INSECTOID, Diet.HERBIVORE, SizeClass.TINY, set()) is KeystoneRole.POLLINATOR
    assert keystone_of(BodyPlan.QUADRUPED, Diet.SCAVENGER, SizeClass.LARGE, set()) is KeystoneRole.SCAVENGER
    assert keystone_of(BodyPlan.QUADRUPED, Diet.HERBIVORE, SizeClass.MEDIUM, {CreatureTrait.AMPHIBIOUS}) is KeystoneRole.DAM_BUILDER
    assert trophic_level(Diet.CARNIVORE, SizeClass.HUGE) is TrophicLevel.APEX
    assert trophic_level(Diet.SOUL, SizeClass.HUGE) is None


def test_evolved_traits_shield_prey_and_spare_the_wary() -> None:
    rules = tuned_rules()
    assert escape(rules, {EvolvedTrait.SPEED: 100, EvolvedTrait.CAMOUFLAGE: 100}) < escape(rules, {}) == 1.0
    assert wary(rules, {EvolvedTrait.WARINESS: 100}) < 1.0
    assert fecund(rules, {EvolvedTrait.FECUNDITY: 100}) > 1.0 > fecund(rules, {EvolvedTrait.FECUNDITY: 0})
    assert cold_reach(rules, {EvolvedTrait.COLD_TOLERANCE: 100}) == rules.trait_evolution.cold_reach


async def test_hunted_ranges_grow_wary_and_a_distant_range_stands_apart(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, trait_evolution={"hunting_pressure": 10})
    deer = await beast_kind(session, world, "Reed Deer", world.regions[0].id)
    await profile_of(ctx, deer)
    row = await session.get(SpeciesRangeRow, (deer.id, world.regions[0].id))
    assert row is not None
    row.hunted = 5
    tally = EvolutionTally()
    await evolve_traits(ctx, tally)
    assert tally.seeded == 1
    wariness = await session.get(SpeciesTraitRow, (deer.id, world.regions[0].id, EvolvedTrait.WARINESS))
    assert wariness is not None
    wariness.mean = 50
    wariness.variance = 0
    before = wariness.mean
    await evolve_traits(ctx, tally)
    assert wariness.mean == before + 10
    session.add(SpeciesRangeRow(species_entity_id=deer.id, region_entity_id=world.regions[1].id, abundance=40, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    for trait in EvolvedTrait:
        session.add(SpeciesTraitRow(species_entity_id=deer.id, region_entity_id=world.regions[1].id, trait=trait, mean=95, variance=0, locked=[]))
    await session.flush()
    assert await apart(session, ctx.rules, deer.id, world.regions[1].id)
    fawn = await entity(session, "Marsh Deer", EntityType.SPECIES, SpeciesStats(hp=30), world_id=world.world.id)
    await mark(ctx, deer, PackageKind.DIVINE_BLESSING, blessing=True, source_node_id=world.son.id)
    assert await inherit_traits(session, deer.id, fawn.id, world.regions[1].id, ctx.epoch) == len(EvolvedTrait)
    assert await session.get(LineageMarkRow, (fawn.id, PackageKind.DIVINE_BLESSING)) is not None


async def test_two_kinds_in_one_niche_cannot_both_hold_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, niches={"displacement_pct": 0, "exclusion_loss": 10})
    region = world.regions[0].id
    strong = await beast_kind(session, world, "Grey Hare", region, abundance=60)
    weak = await beast_kind(session, world, "Pale Hare", region, abundance=20)
    for species in (strong, weak):
        await profile_of(ctx, species)
    tally = NicheTally()
    await compete(ctx, tally)
    loser = await session.get(SpeciesRangeRow, (weak.id, region))
    winner = await session.get(SpeciesRangeRow, (strong.id, region))
    assert loser is not None and winner is not None
    assert loser.abundance == 10
    assert winner.abundance == 60


async def test_a_level_above_its_bound_starves(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, trophic={"efficiency_pct": 1, "collapse": 20})
    region = world.regions[0].id
    grazer = await beast_kind(session, world, "Field Ox", region, abundance=80)
    profile = await profile_of(ctx, grazer)
    profile.diet = Diet.HERBIVORE
    await session.flush()
    await balance_food_chain(ctx, TrophicTally())
    row = await session.get(SpeciesRangeRow, (grazer.id, region))
    level = await session.get(TrophicLevelRow, (region, TrophicLevel.HERBIVORE))
    assert row is not None and level is not None
    assert level.biomass == 80 and level.cap < 80
    assert row.abundance < 80


async def test_keystones_serve_their_land_and_their_loss_is_felt(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    region = world.regions[0].id
    bee = await beast_kind(session, world, "Gold Bee", region, abundance=80)
    profile = await profile_of(ctx, bee)
    profile.keystone = KeystoneRole.POLLINATOR
    await session.flush()
    await keep_services(ctx, KeystoneTally())
    service = await session.get(EcosystemServiceRow, (region, KeystoneRole.POLLINATOR))
    assert service is not None and service.strength == 80
    assert pollination(ctx.rules, {KeystoneRole.POLLINATOR: 80}) > 1.0
    range_row = await session.get(SpeciesRangeRow, (bee.id, region))
    assert range_row is not None
    range_row.abundance = 0
    await session.flush()
    tally = KeystoneTally()
    await keep_services(ctx, tally)
    assert tally.lost == 1
    assert pollination(ctx.rules, {KeystoneRole.POLLINATOR: 0}) < 1.0


async def test_the_herds_of_a_fallen_town_run_wild_and_step_back(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, feral={"revert_epochs": 1})
    town = await settlement(session, "Ashby", world, world.regions[0])
    goat = await beast_kind(session, world, "Hill Goat", world.regions[1].id)
    profile = await profile_of(ctx, goat)
    profile.stage = DomesticationStage.DOMESTICATED
    profile.stage_epoch = 0
    session.add(HerdRow(community_entity_id=town.id, species_entity_id=goat.id, head=30, stage=DomesticationStage.DOMESTICATED, locked=[]))
    town.status = EntityStatus.DESTROYED
    town.end_epoch = 1
    await session.flush()
    tally = FeralTally()
    await run_wild(ctx, tally)
    assert tally.released == 1
    assert await session.get(HerdRow, (town.id, goat.id)) is None
    assert await session.get(SpeciesRangeRow, (goat.id, world.regions[0].id)) is not None
    assert profile.feral_epoch == ctx.epoch
    assert profile.stage is DomesticationStage.HERDED
    profile.stage_epoch = ctx.epoch - 1
    await run_wild(ctx, tally)
    assert profile.stage is DomesticationStage.TAMED


async def sickness(session: AsyncSession, world: CoreWorld) -> EntityRow:
    disease = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(virulence=40, lethality=20), world_id=world.world.id)
    session.add(
        DiseaseProfileRow(
            disease_entity_id=disease.id,
            vector=DiseaseVector.AIR,
            virulence=40,
            lethality=20,
            chronic_rate=0,
            incubation=1,
            target_functions=[],
            climate_affinity=ClimateAffinity.ANY,
            immunity_epochs=4,
            mutation_rate=5,
            stigma=10,
            cure_level=5,
            locked=[],
        )
    )
    await session.flush()
    return disease


async def test_pathogens_resist_treatment_bear_the_cold_and_answer_to_responses(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    disease = await sickness(session, world)
    profile = await session.get(DiseaseProfileRow, disease.id)
    assert profile is not None
    profile.resistance = 100
    assert resisted(rules, profile, 0.5) > 0.5
    profile.cold_tolerance = 100
    cold = RegionEnvironmentRow(temperature_band=TemperatureBand.COLD)
    assert tolerance_fit(profile, cold) > 1.0
    assert answered(rules, {PlagueResponse.QUARANTINE}) < 1.0 < answered(rules, {PlagueResponse.PRAYER})


async def test_a_quarantine_seals_the_land_and_a_found_cure_belongs_to_its_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    disease = await sickness(session, world)
    town = await settlement(session, "Ashby", world, world.regions[0])
    row = await take_up(ctx, town, disease.id, PlagueResponse.QUARANTINE)
    assert row.until_epoch == ctx.epoch + ctx.rules.plague_responses.length
    assert await session.get(QuarantineRow, world.regions[0].id) is not None
    seat = await entity(session, "House of Healing", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=seat.id, kind=StructureKind.HOSPITAL))
    research = CureResearchRow(institution_entity_id=seat.id, disease_entity_id=disease.id, points=200, specimens=1, started_epoch=0, locked=[])
    session.add(research)
    await session.flush()
    await found_cure(ctx, research, seat)
    assert research.cured_epoch == ctx.epoch
    assert await session.get(DiseaseCureRow, (disease.id, town.id)) is not None
    assert ResearchTally().cured == 0


async def test_lands_grow_toward_forest_and_fire_sets_them_back(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, biome_succession={"rate": 100, "fire_pct": 0})
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    ground.succession = SuccessionStage.GRASSLAND
    ground.succession_progress = 99
    ground.base_forest = 90
    ground.farmed = 0
    ground.grazed = 0
    ground.base_wetland = 0
    ground.wetland = 0
    ground.temperature = 15
    ground.rainfall = 60
    ground.soil_fertility = 60
    await session.flush()
    tally = SuccessionTally()
    await grow_lands(ctx, tally)
    assert ground.succession is SuccessionStage.SHRUBLAND
    ground.succession = SuccessionStage.OLD_FOREST
    assert burn_back(ground, ctx.epoch)
    assert ground.succession is SuccessionStage.SHRUBLAND
    assert STAGE_COVER[ground.succession] < STAGE_COVER[SuccessionStage.OLD_FOREST]


async def test_world_cycles_turn_and_their_carbon_feeds_the_air(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    await turn_cycles(ctx, CycleTally())
    cycle = await session.get(WorldCycleRow, world.world.id)
    assert cycle is not None
    cycle.carbon_in, cycle.carbon_out = 9, 2
    assert carbon_flux(cycle) == 1
    physics = WorldPhysicsRow(world_id=world.world.id, carbon_dioxide=5, nitrogen=70, pressure=1.0, volcanism=0, locked=[])
    assert move_carbon(ctx, physics, 0.0, cycle) == 1
    assert physics.carbon_dioxide == 6


async def test_a_raised_land_keeps_its_height_and_a_land_without_coast_cannot_sink(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    before = ground.elevation_mean
    await shape_land(ctx, world.regions[0].id, LandAct.RAISE_LAND, None, fiery=False)
    assert ground.elevation_mean == min(100, before + ctx.rules.land_shaping.step)
    assert "elevation_mean" in ground.locked
    ground.coast_kind = CoastKind.HARBOUR_SITE
    ground.elevation_mean = ctx.rules.land_shaping.coast_lift
    await shape_land(ctx, world.regions[0].id, LandAct.RAISE_LAND, None, fiery=False)
    assert ground.coast_kind is CoastKind.NONE
    assert "coast_kind" in ground.locked
    await session.flush()
    try:
        await shape_land(ctx, world.regions[0].id, LandAct.SINK_COAST, None, fiery=False)
    except Exception as error:
        assert "coast" in str(error)
    else:
        raise AssertionError("a landlocked land sank")


async def test_set_traits_are_held_and_repairs_drop_carriers_of_the_vanished(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session)
    deer = await beast_kind(session, world, "Reed Deer", world.regions[0].id)
    await profile_of(ctx, deer)
    row = await set_trait(ctx, deer.id, world.regions[0].id, EvolvedTrait.SPEED, mean=90, variance=None)
    assert row.mean == 90 and "mean" in row.locked
    assert len(list(await session.scalars(select(SpeciesTraitRow).where(SpeciesTraitRow.species_entity_id == deer.id)))) == len(EvolvedTrait)
    assert await mend_evolution_links(session, ctx.epoch) == 0


def test_answers_follow_a_communitys_values_and_mercy_resents_a_quarantine() -> None:
    lawful = {ValueAxis.LAW: 80}
    tender = {ValueAxis.KINSHIP: 80, ValueAxis.MERCY: 80}
    assert leaning(lawful, PlagueResponse.QUARANTINE) > leaning(lawful, PlagueResponse.PRAYER)
    assert resentment(tender) > resentment({}) > resentment(lawful)


async def test_crowds_take_up_a_spreading_symptom(session: AsyncSession, world: CoreWorld) -> None:
    disease = await sickness(session, world)
    profile = await session.get(DiseaseProfileRow, disease.id)
    assert profile is not None
    assert take_symptom(profile, True)
    assert DiseaseTarget.BREATH.value in profile.target_functions
    assert not take_symptom(profile, True)


async def test_a_cursed_kind_carries_the_curse_down_its_line(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, lineages={"taint_pct": 0})
    wolf = await beast_kind(session, world, "Ash Wolf", world.regions[0].id)
    await profile_of(ctx, wolf)
    await bond(session, world.son.id, wolf.id, BondKind.CURSED)
    await mark_lineages(ctx, LineageTally())
    row = await session.get(LineageMarkRow, (wolf.id, PackageKind.VOID_TAINT))
    assert row is not None and not row.blessing and row.source_node_id == world.son.id


async def test_a_town_that_drives_out_its_sick_sends_them_to_a_colony_and_a_loosed_breed_turns_invasive(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, epidemiology={"colony_min": 1, "expel_pct": 50})
    disease = await sickness(session, world)
    town = await settlement(session, "Ashby", world, world.regions[0], population=2000)
    session.add(
        OutbreakRow(
            disease_entity_id=disease.id,
            region_entity_id=world.regions[0].id,
            path=SpreadPath.ORIGIN,
            severity=40,
            infected=1000,
            dead=0,
            started_epoch=0,
            locked=[],
        )
    )
    await session.flush()
    await take_up(ctx, town, disease.id, PlagueResponse.EXPEL_SICK)
    book = await DiseaseBook.load(session, ctx.rules, ctx.epoch)
    assert await expel_sick(ctx, book) > 0
    goat = await beast_kind(session, world, "Hill Goat", world.regions[1].id)
    profile = await profile_of(ctx, goat)
    profile.stage = DomesticationStage.DOMESTICATED
    herd = HerdRow(community_entity_id=town.id, species_entity_id=goat.id, head=30, stage=DomesticationStage.DOMESTICATED, locked=[])
    session.add(herd)
    await session.flush()
    await release_herd(ctx, herd)
    assert await has_flag(session, goat.id, EntityFlag.INVASIVE)


def test_a_people_that_reviles_every_response_still_weighs_each_above_zero() -> None:
    scorn = dict.fromkeys(ValueAxis, -PERCENT)
    assert all(leaning(scorn, response) > 0 for response in PlagueResponse)
    assert leaning(dict.fromkeys(ValueAxis, PERCENT), PlagueResponse.QUARANTINE) > leaning(scorn, PlagueResponse.QUARANTINE)
