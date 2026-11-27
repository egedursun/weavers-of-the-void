import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.physics import StarPhysicsRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.engine.cosmos.orbits import Sky, bring_into_livable, derive, sky_of, surface_temperature
from aerona.engine.cosmos.stellar import band_of_light, inferred_mass, luminosity_of, luminosity_shifts, refresh
from aerona.engine.cosmos.systems import systems_of
from aerona.rules.registry import Rules

YEAR_LOCK = "year_length_days"
WARMING_LOCKS = frozenset({"albedo", "water_vapour"})
DWELLERS = (EntityType.PEOPLE, EntityType.SETTLEMENT)
CALENDAR_FIELDS = ("season_count", "day_length_hours")


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


def lit_now(rules: Rules, star: StarRow, own: StarPhysicsRow, shift_pct: int) -> StarPhysicsRow:
    current = StarPhysicsRow(**{column.key: getattr(own, column.key) for column in StarPhysicsRow.__table__.columns})
    refresh(rules, star, current, shift_pct)
    return current


async def sky_now(session: AsyncSession, rules: Rules, world: WorldRow, physics: WorldPhysicsRow) -> Sky | None:
    star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
    own = await session.get(StarPhysicsRow, star.id) if star is not None else None
    if star is None or own is None:
        return None
    lit = lit_now(rules, star, own, (await luminosity_shifts(session)).get(star.id, 0))
    return sky_of(rules, world, physics, stars={star.id: star}, star_physics={star.id: lit}, systems=await systems_of(session))


async def homes_too_harsh(session: AsyncSession) -> list[int]:
    rules = await CosmosRepository(session).rules()
    found: list[int] = []
    for world in await peopled_planets(session):
        physics = await session.get(WorldPhysicsRow, world.id)
        if physics is None or held(world.id) or set(physics.locked or []) >= WARMING_LOCKS or "surface_temperature" in (physics.locked or []):
            continue
        sky = await sky_now(session, rules, world, physics)
        if sky is None or not sky.lights:
            continue
        temperature = surface_temperature(rules, world, physics, sky.insolation, None)
        if rules.orbits.livable_low_kelvin <= temperature <= rules.orbits.livable_high_kelvin:
            continue
        trial = WorldPhysicsRow(**{column.key: getattr(physics, column.key) for column in WorldPhysicsRow.__table__.columns})
        bring_into_livable(rules, world, trial, sky=sky, parent=None)
        if (trial.albedo, trial.water_vapour) != (physics.albedo, physics.water_vapour):
            found.append(world.id)
    return found


async def settle_home_climate(session: AsyncSession, world_id: int) -> None:
    world = await session.get(WorldRow, world_id)
    physics = await session.get(WorldPhysicsRow, world_id)
    if world is None or physics is None or world.star_id is None:
        return
    rules = await CosmosRepository(session).rules()
    star = await session.get(StarRow, world.star_id)
    own = await session.get(StarPhysicsRow, world.star_id)
    if star is None or own is None:
        return
    refresh(rules, star, own, (await luminosity_shifts(session)).get(star.id, 0))
    sky = sky_of(rules, world, physics, stars={star.id: star}, star_physics={star.id: own}, systems=await systems_of(session))
    bring_into_livable(rules, world, physics, sky=sky, parent=None)
    derive(rules, world, physics, sky=sky, moons=[], parent=None, rogue=set(), shards=False)


async def orbit_moves(session: AsyncSession) -> list[tuple[StateChangeRow, StateChangeRow]]:
    locks = await session.scalars(
        select(StateChangeRow)
        .where(
            StateChangeRow.table_name == WorldRow.__tablename__,
            StateChangeRow.field == "calendar_locked",
            StateChangeRow.actor_kind == ActorKind.SYSTEM,
            StateChangeRow.after_text.contains(YEAR_LOCK),
        )
        .order_by(StateChangeRow.id)
    )
    found: list[tuple[StateChangeRow, StateChangeRow]] = []
    for lock in locks:
        move = await session.scalar(
            select(StateChangeRow)
            .where(
                StateChangeRow.table_name == WorldRow.__tablename__,
                StateChangeRow.node_id == lock.node_id,
                StateChangeRow.field == "orbit",
                StateChangeRow.actor_kind == ActorKind.SYSTEM,
                StateChangeRow.epoch == lock.epoch,
                StateChangeRow.id < lock.id,
            )
            .order_by(StateChangeRow.id.desc())
            .limit(1)
        )
        if move is not None and move.before_number is not None:
            found.append((move, lock))
    return found


async def homes_moved_off_their_orbit(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for move, _ in await orbit_moves(session):
        world = await session.get(WorldRow, move.node_id) if move.node_id is not None else None
        if world is None or world.parent_world_id is not None or held(world.id) or "orbit" in (world.locked or []) or YEAR_LOCK not in world.calendar_locked:
            continue
        if move.after_number is not None and abs(world.orbit - move.after_number) < 1e-6 and world.id not in found:
            found.append(world.id)
    return found


async def later_calendar_changes(session: AsyncSession, world_id: int, since: StateChangeRow) -> list[StateChangeRow]:
    return list(
        await session.scalars(
            select(StateChangeRow)
            .where(
                StateChangeRow.node_id == world_id,
                StateChangeRow.id > since.id,
                StateChangeRow.actor_kind == ActorKind.ENGINE,
                StateChangeRow.table_name.in_((WorldRow.__tablename__, WorldSeasonRow.__tablename__)),
            )
            .order_by(StateChangeRow.id)
        )
    )


async def restore_seasons(session: AsyncSession, world: WorldRow, changes: list[StateChangeRow]) -> None:
    dropped = [change for change in changes if change.table_name == WorldSeasonRow.__tablename__ and change.operation is LedgerOperation.DELETE]
    first = {change.field: change for change in reversed(changes) if change.table_name == WorldRow.__tablename__ and change.field in CALENDAR_FIELDS}
    for field, change in first.items():
        if change.before_number is not None and field not in world.calendar_locked:
            setattr(world, field, round(change.before_number))
    if not dropped or "season_count" not in first:
        return
    await session.execute(delete(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id))
    await session.flush()
    columns = {column.key for column in WorldSeasonRow.__table__.columns}
    for change in dropped:
        row = json.loads(change.before_text or "{}")
        session.add(WorldSeasonRow(**{key: value for key, value in row.items() if key in columns}))
    await session.flush()


async def restore_ground(session: AsyncSession, world_id: int, move: StateChangeRow) -> None:
    physics = await session.get(WorldPhysicsRow, world_id)
    darkened = await session.scalar(
        select(StateChangeRow)
        .where(
            StateChangeRow.table_name == WorldPhysicsRow.__tablename__,
            StateChangeRow.node_id == world_id,
            StateChangeRow.field == "albedo",
            StateChangeRow.actor_kind == ActorKind.SYSTEM,
            StateChangeRow.epoch == move.epoch,
            StateChangeRow.id < move.id,
        )
        .order_by(StateChangeRow.id.desc())
        .limit(1)
    )
    if physics is not None and darkened is not None and darkened.before_number is not None and "albedo" not in (physics.locked or []):
        physics.albedo = round(darkened.before_number)


async def stars_lit_astray(session: AsyncSession) -> list[int]:
    rules = await CosmosRepository(session).rules()
    shifts = await luminosity_shifts(session)
    found: list[int] = []
    for own in await session.scalars(select(StarPhysicsRow).order_by(StarPhysicsRow.star_id)):
        star = await session.get(StarRow, own.star_id)
        if star is None or held(star.id) or "luminosity" in (own.locked or []):
            continue
        current = lit_now(rules, star, own, shifts.get(star.id, 0))
        if abs(current.luminosity - own.luminosity) > own.luminosity * 1e-6 + 1e-9:
            found.append(star.id)
    return found


async def light_star_by_its_kind(session: AsyncSession, star_id: int) -> None:
    star = await session.get(StarRow, star_id)
    own = await session.get(StarPhysicsRow, star_id)
    if star is None or own is None:
        return
    refresh(await CosmosRepository(session).rules(), star, own, (await luminosity_shifts(session)).get(star_id, 0))


async def return_home_to_its_orbit(session: AsyncSession, world_id: int) -> None:
    world = await session.get(WorldRow, world_id)
    if world is None:
        return
    moves = [move for move, _ in await orbit_moves(session) if move.node_id == world_id]
    lived = moves[0].before_number if moves else None
    if lived is None:
        return
    first = moves[0]
    world.orbit = lived
    await restore_ground(session, world_id, first)
    world.calendar_locked = [key for key in world.calendar_locked if key != YEAR_LOCK]
    await restore_seasons(session, world, await later_calendar_changes(session, world_id, first))
    physics = await session.get(WorldPhysicsRow, world_id)
    if physics is None:
        return
    rules = await CosmosRepository(session).rules()
    sky = await sky_now(session, rules, world, physics)
    if sky is not None:
        derive(rules, world, physics, sky=sky, moons=[], parent=None, rogue=set(), shards=False)
