import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.physics import StarPhysicsRow, StarSystemRow, TerraformingRow, WorldPhysicsRow
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.physics import AirNeed, CosmicFeatureKind, ImpactOutcome, LifeComplexity, SurveyLevel, TerraformAim
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos import physics_control
from aerona.engine.cosmos.impacts import call_impact, deflect_impact, resolve
from aerona.engine.cosmos.lifeforms import life_of, may_arise, world_fit
from aerona.engine.cosmos.stellar import giant_for, main_life, remnant_for
from aerona.engine.cosmos.survey import knows_enough, level_of
from aerona.engine.cosmos.terraform import begin, terraform_cycle
from aerona.engine.phases.physics import settle_heavens
from aerona.rules.registry import Rules
from aerona.services.books.typed import TypedIndex
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, make_region, make_route, make_world, tick


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
    impact = await call_impact(ctx, cosmos.home.id, region.id, None, "The Creator", size=60)
    assert impact.outcome is ImpactOutcome.PENDING and impact.due_epoch == EPOCH + 1
    assert await resolve(tick(session, rules, epoch=EPOCH + 1)) == 1
    assert impact.outcome is ImpactOutcome.STRUCK
    assert impact.crater_place_id is not None
    assert impact.winter_epochs == 60 // rules.impacts.winter_per_size


async def test_a_deflected_body_never_strikes(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    impact = await call_impact(ctx, cosmos.home.id, None, None, "The Creator")
    await deflect_impact(ctx, impact.id, None, "The Creator")
    assert await resolve(tick(session, rules, epoch=EPOCH + 1)) == 0
    assert impact.outcome is ImpactOutcome.DEFLECTED
    with pytest.raises(ValidationFailedError):
        await deflect_impact(ctx, impact.id, None, "The Creator")


async def test_terraforming_moves_the_world_and_ends(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    physics = await session.get(WorldPhysicsRow, cosmos.home.id)
    assert physics is not None
    before = physics.pressure
    await begin(ctx, cosmos.home.id, TerraformAim.THICKEN_AIR, None, "The Creator", step=10, epochs=2)
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
