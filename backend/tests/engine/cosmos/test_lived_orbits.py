import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.physics import StarPhysicsRow, WorldPhysicsRow
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.world import StarType
from aerona.engine.cosmos.orbits import Light, Sky, derive, ground_fit, infer, surface_temperature
from aerona.engine.cosmos.starlife import age_star, stage_epochs
from aerona.engine.cosmos.stellar import luminosity_of, main_luminosity, new_physics, stage_start
from aerona.engine.phases.physics import derive_all
from aerona.rules.registry import Rules
from aerona.services.integrity.habitable_homes import (
    homes_moved_off_their_orbit,
    homes_too_harsh,
    light_star_by_its_kind,
    return_home_to_its_orbit,
    settle_home_climate,
    sky_now,
    stars_lit_astray,
)
from tests.engine.core.factories import CoreWorld, seed_core_world
from tests.engine.cosmos.factories import tick

SEASON_NAMES = ("Nipcu", "Eipjuc", "Ceni", "Nicu")
MOVED_ORBIT = 0.0367
COLD_ORBIT = 1.6
SETTLED_SLACK = 6


def test_a_broken_star_still_sheds_the_light_of_its_mass(rules: Rules) -> None:
    assert luminosity_of(rules, 1.0, StarAge.MAIN, StarType.BROKEN_STAR) == main_luminosity(rules, 1.0)
    assert luminosity_of(rules, 1.0, StarAge.MAIN, StarType.DEAD_STAR) < main_luminosity(rules, 1.0) / 100


async def lit_world(session: AsyncSession, world: CoreWorld) -> WorldPhysicsRow:
    rules = await CosmosRepository(session).rules()
    star = await session.get(StarRow, world.world.star_id)
    assert star is not None
    session.add(new_physics(rules, star, None))
    physics = infer(rules, world.world, star)
    session.add(physics)
    await session.flush()
    return physics


async def test_a_world_outside_the_band_is_habitable_when_its_air_keeps_it_temperate(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    physics = await lit_world(session, world)
    sky = Sky((Light(1.0, world.world.orbit),), 1.0, (5.0, 6.0), 0)
    derive(rules, world.world, physics, sky=sky, moons=[], parent=None, rogue=set(), shards=False)
    assert rules.orbits.livable_low_kelvin <= physics.surface_temperature <= rules.orbits.livable_high_kelvin
    assert physics.habitable


async def test_a_cold_home_is_warmed_where_it_lies_and_never_moved(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await lit_world(session, world)
    world.world.orbit = COLD_ORBIT
    await session.flush()
    assert await homes_too_harsh(session) == [world.world.id]
    await settle_home_climate(session, world.world.id)
    physics = await session.get(WorldPhysicsRow, world.world.id)
    assert physics is not None
    assert world.world.orbit == COLD_ORBIT
    assert physics.habitable
    assert await homes_too_harsh(session) == []


def ledger(world_id: int, table: str, operation: LedgerOperation, actor: ActorKind, **values: object) -> StateChangeRow:
    return StateChangeRow(epoch=10, table_name=table, row_key=json.dumps({"id": world_id}), node_id=world_id, operation=operation, actor_kind=actor, **values)


async def moved_with_its_seasons_lost(session: AsyncSession, world: CoreWorld) -> list[WorldSeasonRow]:
    home = world.world
    await session.execute(delete(WorldSeasonRow).where(WorldSeasonRow.world_id == home.id))
    seasons = [
        WorldSeasonRow(
            world_id=home.id, position=index, name=name, temperature_shift=0, rain_shift=0, growth=50, travel=50, campaign=50, share_pct=25, edited=False
        )
        for index, name in enumerate(SEASON_NAMES)
    ]
    session.add_all(seasons)
    home.season_count, home.day_length_hours, home.axial_tilt = 4, 30, 23
    await session.flush()
    lived = home.orbit
    session.add(ledger(home.id, "worlds", LedgerOperation.UPDATE, ActorKind.SYSTEM, field="orbit", before_number=lived, after_number=MOVED_ORBIT))
    session.add(
        ledger(home.id, "worlds", LedgerOperation.UPDATE, ActorKind.SYSTEM, field="calendar_locked", before_text="[]", after_text='["year_length_days"]')
    )
    home.orbit, home.calendar_locked = MOVED_ORBIT, ["year_length_days"]
    await session.flush()
    session.add(ledger(home.id, "worlds", LedgerOperation.UPDATE, ActorKind.ENGINE, field="season_count", before_number=4, after_number=1))
    session.add(ledger(home.id, "worlds", LedgerOperation.UPDATE, ActorKind.ENGINE, field="day_length_hours", before_number=30, after_number=11568))
    for row in seasons:
        kept = {column.key: getattr(row, column.key) for column in WorldSeasonRow.__table__.columns}
        session.add(ledger(home.id, "world_seasons", LedgerOperation.DELETE, ActorKind.ENGINE, before_text=json.dumps(kept)))
        await session.delete(row)
    await session.flush()
    session.add(
        WorldSeasonRow(
            world_id=home.id, position=0, name="Whole year", temperature_shift=0, rain_shift=0, growth=50, travel=50, campaign=50, share_pct=100, edited=False
        )
    )
    home.season_count, home.day_length_hours = 1, 11568
    await session.flush()
    return seasons


async def test_a_home_an_old_repair_moved_goes_back_with_its_year_days_and_seasons(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    physics = await lit_world(session, world)
    physics.rotation_hours = 30.0
    lived = world.world.orbit
    await moved_with_its_seasons_lost(session, world)
    assert await homes_moved_off_their_orbit(session) == [world.world.id]
    await return_home_to_its_orbit(session, world.world.id)
    await session.flush()
    home = await session.get(WorldRow, world.world.id)
    assert home is not None
    assert home.orbit == lived
    assert "year_length_days" not in home.calendar_locked
    assert (home.season_count, home.day_length_hours) == (4, 30)
    names = list(await session.scalars(select(WorldSeasonRow.name).where(WorldSeasonRow.world_id == home.id).order_by(WorldSeasonRow.position)))
    assert names == list(SEASON_NAMES)
    assert await homes_moved_off_their_orbit(session) == []
    await derive_all(tick(session, rules), quiet=True)
    assert not physics.tidally_locked
    assert home.season_count == len(SEASON_NAMES)
    assert home.day_length_hours == 30
    star = await session.get(StarPhysicsRow, home.star_id)
    assert star is not None


async def test_a_broken_star_left_dim_by_the_old_rule_is_lit_again(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    await lit_world(session, world)
    star = await session.get(StarRow, world.world.star_id)
    own = await session.get(StarPhysicsRow, world.world.star_id)
    assert star is not None and own is not None
    star.star_type, own.mass, own.luminosity = StarType.BROKEN_STAR, 1.0, 0.001
    await session.flush()
    assert await stars_lit_astray(session) == [star.id]
    await light_star_by_its_kind(session, star.id)
    assert own.luminosity == main_luminosity(rules, 1.0)
    assert own.band_inner <= world.world.orbit <= own.band_outer
    assert await stars_lit_astray(session) == []


async def test_a_star_first_counting_its_age_counts_from_the_years_it_has_already_lived(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    await lit_world(session, world)
    star = await session.get(StarRow, world.world.star_id)
    own = await session.get(StarPhysicsRow, world.world.star_id)
    assert star is not None and own is not None
    star.age_stage, star.lifecycle_clock = StarAge.MAIN, None
    full = stage_epochs(rules, star, StarAge.MAIN, own)
    assert full is not None
    own.age_epochs = stage_start(rules, own.mass, StarAge.MAIN) + full // 2
    await age_star(tick(session, rules), star, physics=own)
    assert star.lifecycle_clock == full - full // 2 - 1


async def test_a_home_brought_only_to_the_cold_edge_of_life_is_settled_at_a_temperate_warmth(session: AsyncSession, rules: Rules) -> None:
    world = await seed_core_world(session)
    physics = await lit_world(session, world)
    sky = await sky_now(session, rules, world.world, physics)
    assert sky is not None
    ground_fit(rules, world.world, physics, sky=sky, parent=None, target=rules.orbits.livable_low_kelvin)
    await session.flush()
    edge = surface_temperature(rules, world.world, physics, sky.insolation, None)
    assert rules.orbits.livable_low_kelvin - 1 <= edge <= rules.orbits.livable_low_kelvin + 1
    assert await homes_too_harsh(session) == [world.world.id]
    await settle_home_climate(session, world.world.id)
    await session.flush()
    assert abs(physics.surface_temperature - rules.orbits.settled_home_kelvin) <= SETTLED_SLACK
    assert await homes_too_harsh(session) == []
