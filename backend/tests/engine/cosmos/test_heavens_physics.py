import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.worlds import StarDraft, WorldRepository
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.integrity import MegastructureRow
from aerona.db.tables.physics import CosmicFeatureRow, ImpactEventRow, StarPhysicsRow, StarSystemRow, TerraformingRow, WorldPhysicsRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import WorldAge
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.physics import AirNeed, CosmicFeatureKind, ImpactBody, ImpactOutcome, LifeComplexity, SurveyLevel, TerraformAim
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.domain.enums.world import Atmosphere, Gravity, SkyEventKind, StarType, WorldType
from aerona.domain.models.entity_stats import CelestialStats, PeopleStats, SettlementStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos import physics_control
from aerona.engine.cosmos.climate import band_heat
from aerona.engine.cosmos.features import adopt_comets, return_comets
from aerona.engine.cosmos.impacts import call_impact, deflect_impact, forecast, resolve, warn
from aerona.engine.cosmos.lifeforms import habitability, life_of, may_arise, world_fit
from aerona.engine.cosmos.orbits import Light, Sky, eclipse_period, locks, next_epoch
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.stellar import giant_for, main_life, remnant_for
from aerona.engine.cosmos.survey import knows_enough, level_of, survey_cycle
from aerona.engine.cosmos.terraform import begin, terraform_cycle, wanted_aim
from aerona.engine.demography.peoples import biology_for, ensure_profiles
from aerona.engine.environment.control import set_world_calendar
from aerona.engine.environment.time_control import add_season, set_moons
from aerona.engine.phases.environment import ensure_world_calendar, environment_survey
from aerona.engine.phases.physics import settle_heavens, world_physics
from aerona.engine.phases.sky import calendar_signs
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import stat
from aerona.engine.structures.megastructures import MegaTally
from aerona.engine.structures.megastructures import engine as move_world
from aerona.rules.registry import Rules
from aerona.services.books.typed import TypedIndex
from aerona.services.player.scope import PlayerScope
from aerona.services.player.world_edits import EditWorld, edit_world
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, make_region, make_route, make_world, tick, tuned


def test_mass_sets_lifetime_giant_and_remnant(rules: Rules) -> None:
    assert main_life(rules, 10.0) < main_life(rules, 1.0) < main_life(rules, 0.3)
    assert giant_for(rules, 0.2) is None
    assert giant_for(rules, 1.0) is StarType.RED_GIANT
    assert remnant_for(rules, 1.0) is StarType.WHITE_DWARF
    assert remnant_for(rules, 40.0) is StarType.BLACK_HOLE


async def test_settling_the_heavens_gives_every_star_and_world_its_physics(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    star = await session.get(StarPhysicsRow, cosmos.star.id)
    world = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert star is not None and star.mass > 0 and star.lifetime_epochs > 0
    assert star.system_id is not None
    system = await session.get(StarSystemRow, star.system_id)
    assert system is not None and 0 < system.band_inner < system.band_outer
    assert (system.band_inner, system.band_outer) == (star.band_inner, star.band_outer)
    assert world is not None and world.gravity_g > 0


async def test_a_called_body_strikes_and_leaves_a_crater(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Low Plain", cosmos.home.id)
    impact = await call_impact(ctx, cosmos.home.id, region.id, None, size=60)
    assert impact.outcome is ImpactOutcome.PENDING and impact.due_epoch == EPOCH + 1
    assert await resolve(tick(session, rules, epoch=EPOCH + 1)) == 1
    assert impact.outcome is ImpactOutcome.STRUCK
    assert impact.crater_place_id is not None
    assert impact.winter_epochs == 60 // rules.impacts.winter_per_size


async def test_a_deflected_body_never_strikes(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    impact = await call_impact(ctx, cosmos.home.id, None, None)
    await deflect_impact(ctx, impact.id, None)
    assert await resolve(tick(session, rules, epoch=EPOCH + 1)) == 0
    assert impact.outcome is ImpactOutcome.DEFLECTED
    with pytest.raises(ValidationFailedError):
        await deflect_impact(ctx, impact.id, None)


async def test_terraforming_moves_the_world_and_ends(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None
    before = physics.pressure
    await begin(ctx, cosmos.home.id, TerraformAim.THICKEN_AIR, None, step=10, epochs=2)
    assert await terraform_cycle(ctx) == 1
    assert await terraform_cycle(ctx) == 1
    assert physics.pressure > before
    assert list(await session.scalars(select(TerraformingRow))) == []


async def test_a_people_knows_its_own_world_and_what_it_was_shown(session: AsyncSession, ctx: TickContext, cosmos: Cosmos) -> None:
    far = await make_world(session, "Farhold", star_id=cosmos.star.id)
    people = await make_entity(session, "Vael", EntityType.PEOPLE, PeopleStats(), world_id=cosmos.home.id)
    assert await level_of(session, people.id, cosmos.home.id) is SurveyLevel.MAPPED
    assert await level_of(session, people.id, far.id) is SurveyLevel.UNKNOWN
    survey = await physics_control.set_survey(ctx, people.id, far.id, SurveyLevel.OBSERVED)
    assert "level" in survey.locked
    assert await knows_enough(session, people, far.id, 2)
    assert not await knows_enough(session, people, far.id, 4)


def test_a_world_without_their_air_or_chemistry_suits_a_people_poorly(rules: Rules) -> None:
    table = rules.life_classes
    biology = PeopleBiologyRow(biochemistry=Biochemistry.CARBON_WATER, air=AirNeed.METHANE, gravity_low=0.5, gravity_high=1.6)
    physics = WorldPhysicsRow(pressure=1.0, oxygen=21, methane=0, carbon_dioxide=0, gravity_g=1.0)
    assert world_fit(rules, biology, physics, (Biochemistry.CARBON_WATER,)) == table.air_pct
    biology.air = AirNeed.OXYGEN
    assert world_fit(rules, biology, physics, (Biochemistry.CARBON_WATER,)) == 100
    physics.gravity_g = 3.0
    assert world_fit(rules, biology, physics, (Biochemistry.CARBON_WATER,)) == table.gravity_pct


async def test_a_rogue_world_needs_a_star_or_a_galaxy_to_drift_through(ctx: TickContext) -> None:
    with pytest.raises(ValidationFailedError):
        await physics_control.create_feature(ctx, CosmicFeatureKind.ROGUE_WORLD, "Wanderer", {})


async def test_the_book_keeps_records_whose_owner_is_empty(session: AsyncSession, ctx: TickContext, cosmos: Cosmos) -> None:
    far = await make_world(session, "Farhold")
    await physics_control.create_feature(ctx, CosmicFeatureKind.WORMHOLE, "The Gap", {"world_id": cosmos.home.id, "world_b_id": far.id})
    index = await TypedIndex.load(session, {cosmos.home.id: cosmos.home.name, far.id: far.name})
    table = next(record for record in index.records if record.title == "Cosmic features")
    assert any("The Gap" in row for row in table.rows)


async def test_peoples_can_arise_once_life_has_grown_complex(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    far = await make_world(session, "Farhold", star_id=cosmos.star.id)
    life = await life_of(session, far)
    assert life.complexity is LifeComplexity.COMPLEX
    assert await may_arise(session, rules, far, people=True)
    life.complexity = LifeComplexity.SIMPLE
    assert not await may_arise(session, rules, far, people=True)


async def test_a_known_route_tells_a_people_of_the_world_at_its_end(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    far = await make_world(session, "Farhold")
    people = await make_entity(session, "Vael", EntityType.PEOPLE, PeopleStats(), world_id=cosmos.home.id)
    assert await level_of(session, people.id, far.id) is SurveyLevel.UNKNOWN
    await make_route(session, cosmos.home.id, far.id)
    assert await level_of(session, people.id, far.id) is SurveyLevel.RUMOURED
    assert await knows_enough(session, people, far.id, rules.survey.journey_level)


async def test_the_calendar_survey_keeps_the_tides_the_heavens_derive(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    cosmos.home.tidal_strength = 77
    await ensure_world_calendar(ctx, cosmos.home, 0, cosmos.home.orbit)
    assert cosmos.home.tidal_strength == 77


async def test_a_moon_broken_at_the_roche_limit_leaves_its_world_ringed(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    moon = await make_world(session, "Shard")
    moon.parent_world_id, moon.orbit = cosmos.home.id, 0.01
    await settle_heavens(session, rules)
    await world_physics(tick(session, rules))
    assert moon.world_type is WorldType.SHATTERED
    await world_physics(tick(session, rules, epoch=EPOCH + 1))
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None and physics.ringed


async def test_a_calendar_the_god_sets_outlasts_the_heavens(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    cosmos.home.axial_tilt = 23
    await settle_heavens(session, rules)
    set_world_calendar(rules, cosmos.home, axial_tilt=None, year_length_days=500, day_length_hours=31)
    await add_season(session, cosmos.home.id, "The Long Dark", {}, None)
    count = cosmos.home.season_count
    await world_physics(tick(session, rules))
    assert (cosmos.home.year_length_days, cosmos.home.day_length_hours, cosmos.home.season_count) == (500, 31, count)


async def test_a_world_the_god_makes_heavy_and_airless_stays_so(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    await edit_world(PlayerScope(session, rules), EditWorld(world_id=cosmos.home.id, gravity=Gravity.HIGH, atmosphere=Atmosphere.NONE))
    await world_physics(tick(session, rules))
    assert (cosmos.home.gravity, cosmos.home.atmosphere) == (Gravity.HIGH, Atmosphere.NONE)


async def test_a_great_eclipse_falls_when_its_calendar_comes(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None
    physics.eclipse_years = 3
    period = eclipse_period(rules, physics, cosmos.star)
    assert period is not None
    due = next_epoch(EPOCH, period, cosmos.home.id)
    assert await calendar_signs(tick(session, rules, epoch=due)) >= 1
    eclipses = select(SkyEventRow).where(SkyEventRow.kind == SkyEventKind.ECLIPSE, SkyEventRow.world_id == cosmos.home.id)
    assert [row.epoch for row in await session.scalars(eclipses)] == [due]


async def test_a_settlement_that_explores_a_world_teaches_its_people_to_map_it(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    far = await make_world(session, "Farhold")
    people = await make_entity(session, "Vael", EntityType.PEOPLE, PeopleStats(), world_id=cosmos.home.id)
    town = await make_entity(session, "Ardun", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id)
    await connect(session, town.id, people.id, BondKind.DESCENDS_FROM, EPOCH)
    route = await make_route(session, cosmos.home.id, far.id)
    assert not await knows_enough(session, town, far.id, rules.survey.conquest_level)
    session.add(
        JourneyRow(
            traveller_entity_id=town.id,
            route_id=route.id,
            origin_world_id=cosmos.home.id,
            destination_world_id=far.id,
            intent=JourneyIntent.EXPLORATION,
            epochs_left=0,
            status=JourneyStatus.ARRIVED,
            start_epoch=EPOCH - 1,
            end_epoch=EPOCH,
        )
    )
    await session.flush()
    await survey_cycle(ctx, await Cosmography.load(session))
    assert await level_of(session, people.id, far.id) is SurveyLevel.MAPPED
    assert await knows_enough(session, town, far.id, rules.survey.conquest_level)


async def test_a_people_that_breathes_methane_reshapes_its_air_toward_methane(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    people = await make_entity(session, "Vael", EntityType.PEOPLE, PeopleStats(), world_id=cosmos.home.id)
    biology = biology_for(rules, people, 70, None)
    biology.air = AirNeed.METHANE
    session.add(biology)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None and wanted_aim(biology, physics, rules) is TerraformAim.BREATHABLE_AIR
    before = physics.methane
    await begin(ctx, cosmos.home.id, TerraformAim.BREATHABLE_AIR, people.id, step=10, epochs=1)
    await terraform_cycle(ctx)
    assert physics.methane == before + 10


async def test_a_warned_world_hoards_food_and_flees_the_landing(
    session: AsyncSession, ctx: TickContext, cosmos: Cosmos, monkeypatch: pytest.MonkeyPatch
) -> None:
    region = await make_region(session, "Low Plain", cosmos.home.id)
    refuge = await make_region(session, "High Fell", cosmos.home.id)
    town = await make_entity(session, "Ardun", EntityType.SETTLEMENT, SettlementStats(), world_id=cosmos.home.id, location_id=region.id)
    lot = CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, material=None, quantity=100, quality=50, preserved=0)
    session.add(lot)
    monkeypatch.setattr(RegionAtlas, "neighbour_regions", lambda self, region_id: [refuge.id])
    impact = ImpactEventRow(world_id=cosmos.home.id, region_entity_id=region.id, body=ImpactBody.ASTEROID, size=40, due_epoch=EPOCH + 2, locked=[])
    session.add(impact)
    await session.flush()
    await warn(ctx, cosmos.home, impact, [town])
    assert lot.preserved == ctx.rules.impacts.hoard_pct
    assert town.location_id == refuge.id


async def test_a_body_may_pass_its_world_by(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    impact = ImpactEventRow(world_id=cosmos.home.id, body=ImpactBody.COMET, size=30, due_epoch=EPOCH, locked=[])
    session.add(impact)
    await session.flush()
    assert await resolve(tick(session, tuned(rules, "impacts", miss_pct=100))) == 0
    assert impact.outcome is ImpactOutcome.MISSED


async def test_a_strike_is_remembered_and_spares_the_kinds_that_bear_the_cold(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    hardy = await make_entity(session, "Frostback", EntityType.SPECIES, SpeciesStats(abundance=100), world_id=cosmos.home.id)
    tender = await make_entity(session, "Sunwing", EntityType.SPECIES, SpeciesStats(abundance=100), world_id=cosmos.home.id)
    session.add_all([SpeciesProfileRow(species_entity_id=hardy.id, temperature_min=-40), SpeciesProfileRow(species_entity_id=tender.id, temperature_min=10)])
    region = await make_region(session, "Low Plain", cosmos.home.id)
    await call_impact(ctx, cosmos.home.id, region.id, None, size=80)
    await resolve(tick(session, rules, epoch=EPOCH + 1))
    assert stat(hardy, "abundance") > stat(tender, "abundance")
    assert await session.scalar(select(NotableYearRow).where(NotableYearRow.world_id == cosmos.home.id)) is not None


async def test_a_returning_comet_can_strike(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    await physics_control.create_feature(ctx, CosmicFeatureKind.PERIODIC_COMET, "Ashtail", {"star_id": cosmos.star.id, "next_return_epoch": EPOCH + 1})
    sure = tuned(rules, "impacts", comet_chance=100, miss_pct=0)
    later = tick(session, sure, epoch=EPOCH + 1)
    cosmography = await Cosmography.load(session)
    assert await return_comets(later, cosmography) == 1
    assert await forecast(later, cosmography) == 1


async def test_a_wandering_light_becomes_a_periodic_body(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    light = await make_entity(session, "The Pale Wanderer", EntityType.CELESTIAL, CelestialStats(), world_id=cosmos.home.id)
    light.subtype = "wandering light"
    assert await adopt_comets(ctx) == 1
    row = await session.scalar(select(CosmicFeatureRow).where(CosmicFeatureRow.entity_id == light.id))
    assert row is not None and row.kind is CosmicFeatureKind.WANDERING_STAR and row.period_epochs == rules.cosmic_features.wanderer_period


async def test_a_bright_companion_doubles_the_seasons(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    cosmos.home.axial_tilt = 23
    await settle_heavens(session, rules)
    single = cosmos.home.season_count
    other = await WorldRepository(session).create_star(StarDraft("Second Sun", StarType.YELLOW_DWARF, 70, 0.0, 0.0, 1))
    await physics_control.create_system(ctx, "The Pair", [cosmos.star.id, other.id], 1.5)
    await world_physics(tick(session, rules))
    assert single is not None and cosmos.home.season_count == min(6, single * 2)


def test_an_old_world_locks_farther_from_its_star(rules: Rules) -> None:
    sky = Sky((Light(1.0, 0.2),), 1.0, (0.9, 1.4), 0)
    physics = WorldPhysicsRow()
    young = WorldRow(world_type=WorldType.ORDINARY, orbit=0.2, age_stage=WorldAge.YOUNG)
    dying = WorldRow(world_type=WorldType.ORDINARY, orbit=0.2, age_stage=WorldAge.DYING)
    assert not locks(rules, young, physics, sky)
    assert locks(rules, dying, physics, sky)


async def test_a_people_born_of_a_methane_world_breathes_it_and_bears_its_weight(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    cosmos.home.world_type, cosmos.home.gravity = WorldType.METHANE, Gravity.HIGH
    await settle_heavens(session, rules)
    people = await make_entity(session, "Vael", EntityType.PEOPLE, PeopleStats(), world_id=cosmos.home.id)
    biology, _culture = await ensure_profiles(session, rules, people, None)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None and biology.air is AirNeed.METHANE
    assert await habitability(session, rules, biology, cosmos.home.id) == 100


async def test_a_son_breaks_a_moon_into_a_ring(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    moon = await make_world(session, "Pebble")
    moon.parent_world_id, moon.orbit = cosmos.home.id, 0.2
    await settle_heavens(session, rules)
    await physics_control.break_moon(ctx, moon.id, cosmos.creator.id)
    assert moon.world_type is WorldType.SHATTERED
    await world_physics(tick(session, rules))
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None and physics.ringed
    with pytest.raises(ValidationFailedError):
        await physics_control.break_moon(ctx, cosmos.home.id, cosmos.creator.id)


async def test_moons_the_god_holds_darken_the_sky(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None and physics.eclipse_years == 0
    set_moons(cosmos.home, rules, moon_count=2, tidal_strength=None)
    await world_physics(tick(session, rules))
    assert physics.eclipse_years > 0 and "tidal_strength" in cosmos.home.calendar_locked


async def test_a_moon_keeps_the_year_of_its_planet_and_shares_its_band_of_warmth(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    moon = await make_world(session, "Pale")
    moon.parent_world_id, moon.orbit = cosmos.home.id, 0.02
    cosmos.home.year_length_days = moon.year_length_days = None
    await session.flush()
    await environment_survey(ctx)
    assert moon.year_length_days == cosmos.home.year_length_days
    star = await session.get(StarRow, cosmos.home.star_id) if cosmos.home.star_id is not None else None
    assert band_heat(rules, moon, star, cosmos.home.orbit) == band_heat(rules, cosmos.home, star)


async def test_a_planetary_engine_raised_on_a_moon_moves_the_planet_it_circles(session: AsyncSession, ctx: TickContext, cosmos: Cosmos) -> None:
    moon = await make_world(session, "Tether")
    moon.parent_world_id, moon.orbit = cosmos.home.id, 0.02
    cosmos.home.orbit = 1.0
    town = await make_entity(session, "Anchorage", EntityType.SETTLEMENT, SettlementStats(), world_id=moon.id)
    profile = StructureProfileRow(structure_entity_id=town.id, kind=StructureKind.PLANETARY_ENGINE, host_entity_id=town.id)
    state = MegastructureRow(structure_entity_id=town.id, target_orbit=3.0, locked=[])
    tally = MegaTally()
    await move_world(ctx, profile, 1.0, state, tally)
    assert moon.orbit == 0.02 and cosmos.home.orbit > 1.0 and tally.moved == 1
