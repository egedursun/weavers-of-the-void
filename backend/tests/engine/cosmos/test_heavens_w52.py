import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gravity import GRAVITY, GRAVITY_ORDER
from aerona.catalog.physics_life import AIR_NEEDS, air_fits, first_fitting_air
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.physics import ImpactEventRow, WorldPhysicsRow
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mass_weapons import RemnantKind
from aerona.domain.enums.physics import AirNeed, ImpactBody, ImpactOutcome, LifeEnvironment
from aerona.domain.enums.world import Gravity, WorldType
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.gravity import bear_gravity
from aerona.engine.context import TickContext
from aerona.engine.cosmos.impacts import call_impact, resolve
from aerona.engine.cosmos.lifeforms import place_holds
from aerona.engine.cosmos.orbits import gravity_band
from aerona.engine.phases.physics import settle_heavens
from aerona.engine.primitives.physics import body_strain, launch_delay
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import EPOCH, Cosmos, make_entity, make_region, make_world, tick, tuned


async def physics_of(session: AsyncSession, world_id: int) -> WorldPhysicsRow:
    row = await session.get(WorldPhysicsRow, world_id)
    assert row is not None
    return row


def test_gravity_runs_from_micro_to_crushing_and_wears_bodies_at_its_edges(rules: Rules) -> None:
    assert GRAVITY_ORDER[0] is Gravity.MICRO and GRAVITY_ORDER[-1] is Gravity.CRUSHING
    assert gravity_band(rules, 0.05) is Gravity.MICRO
    assert gravity_band(rules, 1.0) is Gravity.NORMAL
    assert gravity_band(rules, 4.0) is Gravity.CRUSHING
    assert GRAVITY[Gravity.CRUSHING].strain(rules) > GRAVITY[Gravity.NORMAL].strain(rules) == 0


async def test_a_crushing_world_wears_strangers_and_holds_ships_longer(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await settle_heavens(session, rules)
    stranger = await make_entity(session, "Oru", EntityType.MORTAL, MortalStats(hp=60, age=20, lifespan=70), world_id=cosmos.home.id)
    cosmos.home.gravity = Gravity.CRUSHING
    assert body_strain(rules, cosmos.home) == rules.physics.crushing_body_strain
    assert launch_delay(cosmos.home) == GRAVITY[Gravity.CRUSHING].launch > launch_delay(None)
    assert await bear_gravity(tick(session, rules)) >= 1
    assert stat(stranger, "hp") == 60 - rules.physics.crushing_body_strain * rules.physics.strain_endurance // 10


def test_every_chemistry_has_an_air_it_breathes() -> None:
    assert air_fits(AirNeed.HYDROGEN, next(iter(AIR_NEEDS[AirNeed.HYDROGEN].fits)))
    for chemistry in Biochemistry:
        assert air_fits(first_fitting_air(chemistry), chemistry)


async def test_life_holds_under_warmed_ice_and_in_temperate_clouds(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    giant = await make_world(session, "Vast", WorldType.GAS, cosmos.star.id)
    await settle_heavens(session, rules)
    home = await physics_of(session, cosmos.home.id)
    home.cryosphere, home.tectonics, home.hydrosphere = rules.physics.under_ice_cryosphere, rules.physics.under_ice_heat, 60
    assert place_holds(rules, LifeEnvironment.UNDER_ICE, cosmos.home, home)
    home.tectonics = home.volcanism = 0
    assert not place_holds(rules, LifeEnvironment.UNDER_ICE, cosmos.home, home)
    clouds = await physics_of(session, giant.id)
    clouds.surface_temperature = rules.physics.cloud_low_kelvin
    assert place_holds(rules, LifeEnvironment.CLOUD, giant, clouds)
    clouds.surface_temperature = rules.physics.cloud_high_kelvin + 1
    assert not place_holds(rules, LifeEnvironment.CLOUD, giant, clouds)
    assert not place_holds(rules, LifeEnvironment.CLOUD, cosmos.home, home)


async def test_a_wreck_in_orbit_falls_and_strews_its_salvage(session: AsyncSession, ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Scar Fields", cosmos.home.id)
    with pytest.raises(ValidationFailedError):
        await call_impact(ctx, cosmos.home.id, region.id, None, body=ImpactBody.WRECK)
    with pytest.raises(ValidationFailedError):
        await call_impact(ctx, cosmos.home.id, region.id, None, body=ImpactBody.MOON_FRAGMENT)
    remnant = WarRemnantRow(orbit_world_id=cosmos.home.id, kind=RemnantKind.WRECK_FIELD, density=50, locked=[])
    session.add(remnant)
    await session.flush()
    impact = await call_impact(ctx, cosmos.home.id, region.id, cosmos.creator.id, size=40, body=ImpactBody.WRECK)
    assert impact.wreck_remnant_id == remnant.id
    assert await resolve(tick(session, rules, epoch=EPOCH + 1)) == 1
    assert impact.outcome is ImpactOutcome.STRUCK and impact.crater_place_id is not None
    assert remnant.density < 50


async def test_a_natural_body_may_burst_in_the_air_and_leave_no_crater(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Tall Woods", cosmos.home.id)
    impact = ImpactEventRow(world_id=cosmos.home.id, region_entity_id=region.id, body=ImpactBody.COMET, size=40, due_epoch=EPOCH, locked=[])
    session.add(impact)
    await session.flush()
    assert await resolve(tick(session, tuned(tuned(rules, "impacts", airburst_pct=100), "impacts", miss_pct=0))) == 1
    assert impact.outcome is ImpactOutcome.AIRBURST and impact.crater_place_id is None
