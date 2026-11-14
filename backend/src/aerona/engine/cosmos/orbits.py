import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.physics import CosmicFeatureRow, StarPhysicsRow, StarSystemRow, WorldPhysicsRow
from aerona.domain.enums.cosmography import WorldAge
from aerona.domain.enums.physics import CosmicFeatureKind
from aerona.domain.enums.world import Atmosphere, Gravity, WorldType
from aerona.engine.cosmos.climate import band_heat
from aerona.engine.cosmos.star_types import star_heat, star_mechanics
from aerona.engine.cosmos.stellar import hundredths, luminosity_of, typical_mass
from aerona.engine.environment.seasons import NO_SEASON_WORLDS, SEASON_SHAPES, season_count_for
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.rules.registry import Rules

FOURTH = 0.25
GAS_WORLDS = frozenset({WorldType.GAS, WorldType.ICE_GIANT, WorldType.HOT_GIANT, WorldType.RINGED})
SMALL_WORLDS = frozenset({WorldType.DWARF_PLANET, WorldType.ASTEROID_BELT, WorldType.SHATTERED})
ICY_WORLDS = frozenset({WorldType.ICE, WorldType.ICE_SHELL, WorldType.ICE_GIANT})
FIERY_WORLDS = frozenset({WorldType.LAVA, WorldType.FORGE, WorldType.CHTHONIAN})
LIFELESS_WORLDS = frozenset({WorldType.DEAD, WorldType.CORPSE_WORLD, WorldType.CHTHONIAN})
SKYLESS_WORLDS = frozenset({WorldType.DREAM, WorldType.MIRROR, WorldType.VOID_POCKET, WorldType.GODS_PALACE, WorldType.GENERATION_SHIP, WorldType.HOLLOW})
GRAVITY_G: dict[Gravity, float] = {Gravity.LOW: 0.4, Gravity.NORMAL: 1.0, Gravity.HIGH: 1.8}
AIR: dict[Atmosphere, tuple[float, dict[str, int]]] = {
    Atmosphere.NONE: (0.0, {"nitrogen": 0, "oxygen": 0, "carbon_dioxide": 0, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.THIN: (0.3, {"nitrogen": 80, "oxygen": 16, "carbon_dioxide": 4, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.NORMAL: (1.0, {"nitrogen": 78, "oxygen": 21, "carbon_dioxide": 1, "methane": 0, "water_vapour": 0, "exotic_gas": 0}),
    Atmosphere.DENSE: (4.0, {"nitrogen": 75, "oxygen": 18, "carbon_dioxide": 5, "methane": 0, "water_vapour": 2, "exotic_gas": 0}),
    Atmosphere.TOXIC: (1.5, {"nitrogen": 40, "oxygen": 2, "carbon_dioxide": 40, "methane": 8, "water_vapour": 0, "exotic_gas": 10}),
}
TOXIC_GASES = ("carbon_dioxide", "methane", "exotic_gas")
LOCK_REACH_BY_AGE: dict[WorldAge, float] = {WorldAge.YOUNG: 0.5, WorldAge.MATURE: 1.0, WorldAge.OLD: 1.5, WorldAge.DYING: 2.0}


@dataclass(frozen=True)
class Light:
    luminosity: float
    distance: float


@dataclass(frozen=True)
class Sky:
    lights: tuple[Light, ...]
    central_mass: float
    band: tuple[float, float]
    flare: int

    @property
    def insolation(self) -> float:
        return sum(flux(light) for light in self.lights)

    @property
    def companion_share(self) -> float:
        total = self.insolation
        return sum(flux(light) for light in self.lights[1:]) / total if total > 0 else 0.0


def flux(light: Light) -> float:
    return light.luminosity / max(light.distance, 0.01) ** 2


@dataclass(frozen=True)
class Moon:
    mass: float
    orbit: float
    inclination: float


HELD_MOON_SHARE = 0.0123
HELD_MOON_TILT = 5.0


def counted_moons(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, moons: list[Moon]) -> list[Moon]:
    held = world.moon_count or 0
    if "moon_count" not in world.calendar_locked or held <= len(moons):
        return moons
    orbit = hundredths(rules.orbits.roche_orbit_hundredths) * 4
    return [*moons, *[Moon(physics.mass * HELD_MOON_SHARE, orbit, HELD_MOON_TILT)] * (held - len(moons))]


async def planet_of(session: AsyncSession, world: WorldRow) -> WorldRow:
    planet = world
    seen = {world.id}
    while planet.parent_world_id is not None and planet.parent_world_id not in seen:
        parent = await session.get(WorldRow, planet.parent_world_id)
        if parent is None:
            break
        seen.add(parent.id)
        planet = parent
    return planet


def root_of(worlds: dict[int, WorldRow], world: WorldRow) -> WorldRow:
    seen: set[int] = set()
    while world.parent_world_id is not None and world.id not in seen and world.parent_world_id in worlds:
        seen.add(world.id)
        world = worlds[world.parent_world_id]
    return world


def sky_of(
    rules: Rules,
    root: WorldRow,
    physics: WorldPhysicsRow,
    *,
    stars: dict[int, StarRow],
    star_physics: dict[int, StarPhysicsRow],
    systems: dict[int, StarSystemRow],
) -> Sky:
    star = stars.get(root.star_id) if root.star_id is not None else None
    if star is None:
        return Sky((), 1.0, (0.0, 0.0), 0)
    own = star_physics.get(star.id)
    mass = own.mass if own is not None else typical_mass(rules, star.star_type)
    lights = [Light(own.luminosity if own is not None else luminosity_of(rules, mass, star.age_stage, star.star_type), root.orbit)]
    central = mass
    system = systems.get(own.system_id) if own is not None and own.system_id is not None else None
    if system is not None:
        share = rules.orbits.circumbinary_share_pct / PERCENT if physics.circumbinary else 1.0
        for other_id, other in sorted(star_physics.items()):
            if other_id == star.id or other.system_id != system.id or other_id not in stars:
                continue
            distance = root.orbit if physics.circumbinary else max(0.01, abs(system.separation - root.orbit))
            lights.append(Light(other.luminosity * share, distance))
            if physics.circumbinary:
                central += other.mass
    total = sum(light.luminosity for light in lights)
    inner = hundredths(rules.stellar_evolution.habitable_inner_hundredths) * math.sqrt(total)
    outer = hundredths(rules.stellar_evolution.habitable_outer_hundredths) * math.sqrt(total)
    return Sky(tuple(lights), central, (inner, outer), star.radiation)


def year_days(rules: Rules, orbit: float, central_mass: float) -> int:
    table = rules.seasons
    period = math.sqrt(max(orbit, 0.01) ** 3 / max(central_mass, 0.01))
    return clamp_int(round_half_up(table.year_days_base * period), table.year_days_min, table.year_days_max)


def equilibrium(rules: Rules, insolation: float, albedo: int) -> float:
    return float(rules.orbits.equilibrium_constant * max(0.0, insolation * (PERCENT - albedo) / PERCENT) ** FOURTH)


def greenhouse(rules: Rules, physics: WorldPhysicsRow) -> float:
    table = rules.orbits
    pressure = physics.pressure
    return pressure * (
        table.greenhouse_base
        + physics.carbon_dioxide * table.greenhouse_co2
        + physics.methane * table.greenhouse_methane
        + physics.water_vapour * table.greenhouse_water
    )


def tidal_warmth(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, parent: WorldPhysicsRow | None) -> float:
    if world.parent_world_id is None or parent is None:
        return 0.0
    distance = max(world.orbit, 0.01) / hundredths(rules.orbits.roche_orbit_hundredths * 2)
    return rules.orbits.tidal_heat * parent.mass / max(distance, 1.0) ** 3


def stony_share(physics: WorldPhysicsRow) -> float:
    body = physics.iron + physics.rock + physics.ice + physics.gas
    return (physics.iron + physics.rock) / body if body > 0 else 1.0


def surface_temperature(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, insolation: float, parent: WorldPhysicsRow | None) -> float:
    inner = rules.orbits.internal_heat * physics.volcanism / PERCENT * stony_share(physics)
    return equilibrium(rules, insolation, physics.albedo) + greenhouse(rules, physics) + tidal_warmth(rules, world, physics, parent) + inner


def heat_of(rules: Rules, temperature: float) -> int:
    table = rules.orbits
    value = (temperature - table.reference_temperature) / 10 * table.heat_per_ten_kelvin
    return clamp_int(round_half_up(value), -table.heat_cap, table.heat_cap)


def gravity_band(rules: Rules, gravity: float) -> Gravity:
    if gravity < hundredths(rules.orbits.low_gravity_g_hundredths):
        return Gravity.LOW
    if gravity > hundredths(rules.orbits.high_gravity_g_hundredths):
        return Gravity.HIGH
    return Gravity.NORMAL


def air_band(rules: Rules, physics: WorldPhysicsRow) -> Atmosphere:
    table = rules.orbits
    if physics.pressure < hundredths(table.no_air_hundredths):
        return Atmosphere.NONE
    if sum(getattr(physics, gas) for gas in TOXIC_GASES) >= table.toxic_share:
        return Atmosphere.TOXIC
    if physics.pressure < hundredths(table.thin_air_hundredths):
        return Atmosphere.THIN
    if physics.pressure > hundredths(table.dense_air_hundredths):
        return Atmosphere.DENSE
    return Atmosphere.NORMAL


def locks(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, sky: Sky) -> bool:
    if world.world_type is WorldType.TIDALLY_LOCKED or world.parent_world_id is not None:
        return world.world_type is WorldType.TIDALLY_LOCKED or world.orbit <= hundredths(rules.orbits.roche_orbit_hundredths) * 4
    if not sky.lights:
        return False
    reach = hundredths(rules.orbits.lock_orbit_hundredths) * float(sky.central_mass ** (1 / 3)) * LOCK_REACH_BY_AGE[world.age_stage]
    return world.orbit < reach


def eclipse_years(rules: Rules, moons: list[Moon], lights: int, circumbinary: bool) -> int:
    if not lights:
        return 0
    table = rules.orbits
    if not moons:
        return table.eclipse_years_base * 4 if circumbinary else 0
    best = min(table.eclipse_years_base * (1 + abs(moon.inclination) / table.eclipse_inclination_degrees) for moon in moons)
    return max(1, round_half_up(best / len(moons)))


def tides(rules: Rules, physics: WorldPhysicsRow, moons: list[Moon]) -> int:
    nearest = hundredths(rules.orbits.roche_orbit_hundredths) * 2
    strength = sum(
        rules.orbits.tide_per_moon_mass * (moon.mass / max(physics.mass, 0.01) * PERCENT) * (nearest / max(moon.orbit, nearest)) ** 3 for moon in moons
    )
    return clamp_percent(round_half_up(strength))


def infer(rules: Rules, world: WorldRow, star: StarRow | None) -> WorldPhysicsRow:
    radius = 10.0 if world.world_type in GAS_WORLDS else 0.3 if world.world_type in SMALL_WORLDS else 1.6 if world.world_type is WorldType.SUPER_EARTH else 1.0
    if world.parent_world_id is not None and world.world_type not in GAS_WORLDS:
        radius = min(radius, 0.3)
    gravity = GRAVITY_G[world.gravity]
    pressure, mix = AIR[world.atmosphere]
    physics = WorldPhysicsRow(
        world_id=world.id,
        eccentricity=0.02,
        inclination=1.0,
        argument=0.0,
        mass=round(gravity * radius**2, 3),
        radius=radius,
        iron=70 if world.world_type is WorldType.IRON else 5 if world.world_type in GAS_WORLDS else 30,
        rock=20 if world.world_type is WorldType.IRON else 5 if world.world_type in GAS_WORLDS else 60,
        ice=60 if world.world_type in ICY_WORLDS else 5,
        gas=85 if world.world_type in GAS_WORLDS else 0,
        exotic=40 if world.world_type in (WorldType.CRYSTAL, WorldType.CARBON) else 0,
        rotation_hours=float(world.day_length_hours or 24),
        pressure=pressure * (90.0 if world.world_type is WorldType.GREENHOUSE else 1.0),
        **mix,
        albedo=70 if world.world_type in ICY_WORLDS else 30,
        tectonics=0 if world.world_type in LIFELESS_WORLDS else 50,
        volcanism=90 if world.world_type in FIERY_WORLDS else 0 if world.world_type in LIFELESS_WORLDS else 20,
        hydrosphere=clamp_percent(round_half_up(world.terrain_sea * PERCENT)),
        cryosphere=80 if world.world_type in ICY_WORLDS else 10,
        circumbinary=False,
        locked=[],
    )
    if world.world_type is WorldType.METHANE:
        physics.methane = 30
        physics.nitrogen = max(0, physics.nitrogen - 30)
    return physics


ORBIT_INPUTS = frozenset({"eccentricity", "inclination", "argument", "circumbinary"})
DERIVED_WORLD_FIELDS = frozenset({"gravity", "atmosphere", "year_length_days", "day_length_hours", "season_count", "tidal_strength"})


def take(physics: WorldPhysicsRow, key: str, value: object) -> None:
    if key not in physics.locked:
        setattr(physics, key, value)


def match_gravity(physics: WorldPhysicsRow, gravity: Gravity) -> None:
    take(physics, "mass", round(GRAVITY_G[gravity] * physics.radius**2, 3))
    take(physics, "gravity_g", GRAVITY_G[gravity])


def match_air(physics: WorldPhysicsRow, atmosphere: Atmosphere) -> None:
    pressure, mix = AIR[atmosphere]
    take(physics, "pressure", pressure)
    for key, value in mix.items():
        take(physics, key, value)


def match_kind(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, star: StarRow | None) -> None:
    fresh = infer(rules, world, star)
    for column in WorldPhysicsRow.__table__.columns:
        if column.key not in ORBIT_INPUTS and column.key not in ("world_id", "locked"):
            take(physics, column.key, getattr(fresh, column.key))


def calibrate(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, *, star: StarRow | None, sky: Sky, parent: WorldPhysicsRow | None, orbit: float) -> None:
    if not sky.lights or world.world_type in SKYLESS_WORLDS:
        return
    target = star_heat(rules, star) + band_heat(rules, world, star, orbit)
    best = min(range(0, 96), key=lambda albedo: abs(heat_of(rules, temperature_with(rules, world, physics, sky=sky, parent=parent, albedo=albedo)) - target))
    physics.albedo = best


def temperature_with(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, *, sky: Sky, parent: WorldPhysicsRow | None, albedo: int) -> float:
    held_albedo = physics.albedo
    physics.albedo = albedo
    value = surface_temperature(rules, world, physics, sky.insolation, parent)
    physics.albedo = held_albedo
    return value


def governed(world: WorldRow, sky: Sky, rogue: set[int]) -> bool:
    return world.world_type not in SKYLESS_WORLDS and (bool(sky.lights) or world.id in rogue)


def derive(
    rules: Rules,
    world: WorldRow,
    physics: WorldPhysicsRow,
    *,
    sky: Sky,
    moons: list[Moon],
    parent: WorldPhysicsRow | None,
    rogue: set[int],
    orbit: float,
    shards: bool,
) -> None:
    def put(key: str, value: object) -> None:
        if key not in physics.locked:
            setattr(physics, key, value)

    insolation = sky.insolation
    temperature = surface_temperature(rules, world, physics, insolation, parent)
    gravity = physics.mass / max(physics.radius, 0.01) ** 2
    put("insolation", round(insolation, 4))
    put("surface_temperature", round(temperature, 1))
    put("gravity_g", round(gravity, 3))
    put("escape_velocity", round(math.sqrt(physics.mass / max(physics.radius, 0.01)), 3))
    put("tidally_locked", locks(rules, world, physics, sky))
    put("ringed", shards or world.world_type is WorldType.RINGED or any(moon.orbit < hundredths(rules.orbits.roche_orbit_hundredths) for moon in moons))
    put("aurora", clamp_percent(round_half_up(world.magnetism * sky.flare * rules.orbits.aurora_per_magnetism_pct / PERCENT / PERCENT)))
    put("eclipse_years", eclipse_years(rules, moons, len(sky.lights), physics.circumbinary))
    put("heat_shift", heat_of(rules, temperature) if governed(world, sky, rogue) else 0)
    inner, outer = sky.band
    put("habitable", bool(sky.lights) and inner <= orbit <= outer)


def lose_air(rules: Rules, physics: WorldPhysicsRow) -> bool:
    table = rules.orbits
    if "pressure" in physics.locked or physics.pressure <= 0:
        return False
    if physics.escape_velocity >= hundredths(table.escape_hold_hundredths) or physics.surface_temperature < table.reference_temperature:
        return False
    physics.pressure = max(0.0, round(physics.pressure - hundredths(table.air_loss_hundredths), 3))
    return True


def apply_to_world(rules: Rules, world: WorldRow, physics: WorldPhysicsRow, sky: Sky, moons: list[Moon], *, orbit: float) -> list[str]:
    changed: list[str] = []
    if "gravity" not in world.locked and world.gravity is not gravity_band(rules, physics.gravity_g):
        world.gravity = gravity_band(rules, physics.gravity_g)
        changed.append("gravity")
    if "atmosphere" not in world.locked and world.atmosphere is not air_band(rules, physics):
        world.atmosphere = air_band(rules, physics)
        changed.append("atmosphere")
    calendar = set(world.calendar_locked)
    if sky.lights and "year_length_days" not in calendar:
        root_year = year_days(rules, orbit, sky.central_mass)
        if world.year_length_days != root_year:
            world.year_length_days = root_year
            changed.append("year_length_days")
    if "day_length_hours" not in calendar:
        day = (world.year_length_days or 1) * 24 if physics.tidally_locked else round_half_up(physics.rotation_hours)
        if world.day_length_hours != day:
            world.day_length_hours = max(1, day)
            changed.append("day_length_hours")
    if "season_count" not in calendar and world.axial_tilt is not None:
        count = 1 if physics.tidally_locked or world.world_type in NO_SEASON_WORLDS else season_count_for(rules, world.world_type, world.axial_tilt)
        if count == 1 and physics.eccentricity * PERCENT >= rules.orbits.global_season_eccentricity_pct and not physics.tidally_locked:
            count = 2
        if not physics.circumbinary and not physics.tidally_locked and sky.companion_share * PERCENT >= rules.orbits.binary_season_share_pct:
            count = min(max(SEASON_SHAPES), count * 2)
        if world.season_count != count:
            world.season_count = count
            changed.append("season_count")
    if "tidal_strength" not in calendar:
        strength = tides(rules, physics, moons)
        if world.tidal_strength != strength:
            world.tidal_strength = strength
    return changed


async def rogue_worlds(session: AsyncSession) -> set[int]:
    statement = select(CosmicFeatureRow.world_id).where(
        CosmicFeatureRow.kind == CosmicFeatureKind.ROGUE_WORLD, CosmicFeatureRow.ended_epoch.is_(None), CosmicFeatureRow.world_id.is_not(None)
    )
    return {world_id for world_id in await session.scalars(statement) if world_id is not None}


def great_eclipse_epochs(rules: Rules, physics: WorldPhysicsRow, companions: int) -> int | None:
    if physics.eclipse_years <= 0:
        return None
    years = physics.eclipse_years * rules.orbits.great_eclipse_rarity / (1 + max(0, companions))
    return max(1, round_half_up(years / rules.time.years_per_epoch))


def eclipse_period(rules: Rules, physics: WorldPhysicsRow | None, star: StarRow | None) -> int | None:
    if physics is None:
        return None
    return great_eclipse_epochs(rules, physics, star_mechanics(star.star_type).eclipse_weight(rules) if star is not None else 0)


def transit_epochs(rules: Rules, inner_year: int, outer_year: int, tilt: float) -> int | None:
    reach = rules.orbits.transit_inclination_degrees
    if inner_year <= 0 or inner_year >= outer_year or tilt > reach:
        return None
    meeting_days = 1 / (1 / inner_year - 1 / outer_year)
    years = meeting_days / outer_year * rules.orbits.transit_rarity * (1 + tilt / (reach + 1))
    return max(1, round_half_up(years / rules.time.years_per_epoch))


def next_epoch(epoch: int, period: int, phase: int) -> int:
    return epoch + (-(epoch + phase)) % period


def transit_pairs(rules: Rules, worlds: list[WorldRow], skies: dict[int, WorldPhysicsRow]) -> list[tuple[WorldRow, WorldRow, int]]:
    planets = [world for world in worlds if world.parent_world_id is None and world.star_id is not None]
    pairs: list[tuple[WorldRow, WorldRow, int]] = []
    for outer in planets:
        for inner in planets:
            seen, seer = skies.get(inner.id), skies.get(outer.id)
            if inner.star_id != outer.star_id or inner.orbit >= outer.orbit or seen is None or seer is None:
                continue
            period = transit_epochs(rules, inner.year_length_days or 0, outer.year_length_days or 0, abs(seen.inclination - seer.inclination))
            if period is not None:
                pairs.append((outer, inner, period))
    return sorted(pairs, key=lambda pair: (pair[0].id, pair[1].id))


def transit_phase(outer: WorldRow, inner: WorldRow) -> int:
    return outer.id + inner.id
