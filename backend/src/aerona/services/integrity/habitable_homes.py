from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import StarPhysicsRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.cosmos.orbits import calibrate, derive, sky_of
from aerona.engine.cosmos.stellar import band_of_light, inferred_mass, luminosity_of, temperate_orbit
from aerona.engine.cosmos.systems import systems_of
from aerona.rules.registry import Rules

ORBIT_LOCK = "orbit"
ALBEDO_LOCK = "albedo"
YEAR_LOCK = "year_length_days"
DWELLERS = (EntityType.PEOPLE, EntityType.SETTLEMENT)


def band_for(rules: Rules, star: StarRow, physics: StarPhysicsRow | None) -> tuple[float, float]:
    if physics is not None:
        return physics.band_inner, physics.band_outer
    return band_of_light(rules, luminosity_of(rules, inferred_mass(rules, star), star.age_stage, star.star_type))


async def peopled_planets(session: AsyncSession) -> list[WorldRow]:
    dwelt = select(EntityRow.world_id).where(EntityRow.entity_type.in_(list(DWELLERS)), EntityRow.status == EntityStatus.CANON)
    return list(
        await session.scalars(
            select(WorldRow).where(WorldRow.parent_world_id.is_(None), WorldRow.star_id.is_not(None), WorldRow.id.in_(dwelt)).order_by(WorldRow.id)
        )
    )


async def homes_outside_their_band(session: AsyncSession) -> list[int]:
    rules = await CosmosRepository(session).rules()
    found: list[int] = []
    for world in await peopled_planets(session):
        if world.parent_world_id is not None or ORBIT_LOCK in (world.locked or []) or held(world.id) or world.star_id is None:
            continue
        star = await session.get(StarRow, world.star_id)
        if star is None:
            continue
        inner, outer = band_for(rules, star, await session.get(StarPhysicsRow, star.id))
        if not inner <= world.orbit <= outer:
            found.append(world.id)
    return found


async def move_home_into_band(session: AsyncSession, world_id: int) -> None:
    world = await session.get(WorldRow, world_id)
    star = await session.get(StarRow, world.star_id) if world is not None and world.star_id is not None else None
    if world is None or star is None or world.parent_world_id is not None:
        return
    rules = await CosmosRepository(session).rules()
    own = await session.get(StarPhysicsRow, star.id)
    world.orbit = temperate_orbit(rules, star, own)
    if world.year_length_days and YEAR_LOCK not in world.calendar_locked:
        world.calendar_locked = sorted({*world.calendar_locked, YEAR_LOCK})
    physics = await session.get(WorldPhysicsRow, world.id)
    if physics is None:
        return
    sky = sky_of(rules, world, physics, stars={star.id: star}, star_physics={star.id: own} if own is not None else {}, systems=await systems_of(session))
    if ALBEDO_LOCK not in (physics.locked or []):
        calibrate(rules, world, physics, star=star, sky=sky, parent=None, orbit=world.orbit)
    derive(rules, world, physics, sky=sky, moons=[], parent=None, rogue=set(), orbit=world.orbit, shards=False)
