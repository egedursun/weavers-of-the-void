import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import StarRow
from aerona.db.tables.physics import StarPhysicsRow, StarSystemRow
from aerona.db.write_guard import held
from aerona.domain.enums.physics import SystemRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.ladder import settle_star
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.stellar import band_of_light, physics_of_stars
from aerona.rules.registry import Rules

FULL_TURN = 360.0
INNER_SPEED_CAP = 5.0
INNER_FLOOR = 0.1


def system_name(star: StarRow) -> str:
    return f"System of {star.name}"


async def systems_of(session: AsyncSession) -> dict[int, StarSystemRow]:
    return {row.id: row for row in await session.scalars(select(StarSystemRow).order_by(StarSystemRow.id))}


async def ensure_systems(session: AsyncSession, rules: Rules, epoch: int) -> int:
    stars = {row.id: row for row in await session.scalars(select(StarRow).order_by(StarRow.id))}
    physics = await physics_of_stars(session, rules, list(stars.values()))
    systems = await systems_of(session)
    made = 0
    for star_id, row in sorted(physics.items()):
        star = stars.get(star_id)
        if star is None or (row.system_id is not None and row.system_id in systems) or "system_id" in row.locked:
            continue
        system = StarSystemRow(name=system_name(star), galaxy_id=star.galaxy_id, x=star.x, y=star.y, separation=0.0, created_epoch=max(1, epoch), locked=[])
        session.add(system)
        await session.flush()
        systems[system.id] = system
        row.system_id = system.id
        row.role = SystemRole.PRIMARY
        made += 1
    await settle_systems(session, rules)
    return made


async def settle_systems(session: AsyncSession, rules: Rules) -> None:
    stars = {row.id: row for row in await session.scalars(select(StarRow).order_by(StarRow.id))}
    physics = await physics_of_stars(session, rules, list(stars.values()))
    for system in (await systems_of(session)).values():
        sync_system(rules, system, stars, physics)
    await session.flush()


def members(physics: dict[int, StarPhysicsRow], system_id: int) -> list[int]:
    return sorted(
        (star_id for star_id, row in physics.items() if row.system_id == system_id),
        key=lambda star_id: (physics[star_id].role is not SystemRole.PRIMARY, -physics[star_id].mass, star_id),
    )


def sync_system(rules: Rules, system: StarSystemRow, stars: dict[int, StarRow], physics: dict[int, StarPhysicsRow]) -> None:
    ids = [star_id for star_id in members(physics, system.id) if star_id in stars]
    if not ids:
        return
    primary = stars[ids[0]]
    if "x" not in system.locked:
        system.x = primary.x
    if "y" not in system.locked:
        system.y = primary.y
    if "galaxy_id" not in system.locked:
        system.galaxy_id = primary.galaxy_id
    inner, outer = band_of_light(rules, sum(physics[star_id].luminosity for star_id in ids))
    if "band_inner" not in system.locked:
        system.band_inner = inner
    if "band_outer" not in system.locked:
        system.band_outer = outer
    for star_id in ids[1:]:
        companion = stars[star_id]
        if held(companion.id):
            continue
        if "x" not in companion.locked:
            companion.x = primary.x
        if "y" not in companion.locked:
            companion.y = primary.y
        if "galaxy_id" not in companion.locked:
            companion.galaxy_id = primary.galaxy_id


def turned(rules: Rules, radius: float, x: float, y: float) -> tuple[float, float]:
    reach = math.hypot(x, y)
    if reach <= 0 or radius <= 0:
        return x, y
    speed = min(INNER_SPEED_CAP, radius / max(reach, radius * INNER_FLOOR))
    angle = math.radians(rules.orbits.galactic_turn_degrees * speed % FULL_TURN)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


async def turn_galaxies(ctx: TickContext, cosmography: Cosmography, physics: dict[int, StarPhysicsRow]) -> int:
    moved = 0
    companions = {star_id for star_id, row in physics.items() if row.role is SystemRole.COMPANION and row.system_id is not None}
    for star in sorted(cosmography.stars.values(), key=lambda row: row.id):
        galaxy = cosmography.galaxies.get(star.galaxy_id) if star.galaxy_id is not None else None
        if galaxy is None or held(star.id) or star.id in companions or "x" in star.locked or "y" in star.locked:
            continue
        star.x, star.y = turned(ctx.rules, galaxy.radius, star.x, star.y)
        settle_star(ctx.rules, cosmography, star)
        moved += 1
    return moved


async def join_system(session: AsyncSession, rules: Rules, star: StarRow, system_id: int) -> StarPhysicsRow:
    rows = await physics_of_stars(session, rules, [star])
    row = rows[star.id]
    taken = any(other.system_id == system_id and other.role is SystemRole.PRIMARY and other_id != star.id for other_id, other in rows.items())
    row.system_id = system_id
    row.role = SystemRole.COMPANION if taken else SystemRole.PRIMARY
    await settle_systems(session, rules)
    return row
