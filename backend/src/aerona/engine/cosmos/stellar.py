import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.stars import STAR_AGES
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import GalaxyRow
from aerona.db.tables.physics import StarPhysicsRow
from aerona.db.tables.transform import StarModifierRow
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, StarType
from aerona.engine.cosmos.star_types import brightness_band, star_mechanics
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.rules.registry import Rules

HUNDRED = 100.0
REMNANTS = frozenset({StarType.WHITE_DWARF, StarType.NEUTRON_STAR, StarType.MAGNETAR, StarType.PULSAR, StarType.BLACK_HOLE, *EXTINGUISHED_STAR_TYPES})
GIANTS = frozenset({StarType.RED_GIANT, StarType.YELLOW_GIANT, StarType.RED_SUPERGIANT, StarType.BLUE_SUPERGIANT, StarType.HYPERGIANT})
STAGE_LIGHT: dict[StarAge, float] = {
    StarAge.YOUNG: 0.7,
    StarAge.MAIN: 1.0,
    StarAge.OLD: 50.0,
    StarAge.DYING: 20.0,
    StarAge.DEAD: 0.001,
    StarAge.REBORN: 0.7,
}


def hundredths(value: int) -> float:
    return value / HUNDRED


def typical_mass(rules: Rules, star_type: StarType) -> float:
    return max(0.01, hundredths(star_mechanics(star_type).mass(rules)))


def main_luminosity(rules: Rules, mass: float) -> float:
    return max(1e-6, float(mass ** (rules.stellar_evolution.luminosity_exponent_tenths / 10)))


def luminosity_of(rules: Rules, mass: float, stage: StarAge, star_type: StarType) -> float:
    if star_type in REMNANTS:
        return main_luminosity(rules, mass) * STAGE_LIGHT[StarAge.DEAD]
    if star_type in GIANTS:
        return main_luminosity(rules, mass) * STAGE_LIGHT[StarAge.OLD]
    light = STAGE_LIGHT[stage] if stage is not StarAge.OLD or not is_dwarf(rules, mass) else 1.0
    return main_luminosity(rules, mass) * light


def main_life(rules: Rules, mass: float) -> int:
    table = rules.stellar_evolution
    life = table.sun_life_epochs * mass / main_luminosity(rules, mass)
    return clamp_int(round_half_up(life), 1, table.life_cap_epochs)


def stage_length(rules: Rules, mass: float, stage: StarAge) -> int | None:
    table = rules.stellar_evolution
    life = main_life(rules, mass)
    spec = STAR_AGES[stage]
    if not spec.lasts:
        return None
    share = int(getattr(table, spec.length_rule)) if spec.length_rule is not None else PERCENT
    return clamp_int(round_half_up(life * share / PERCENT), 1, table.life_cap_epochs)


def stage_start(rules: Rules, mass: float, stage: StarAge) -> int:
    young = stage_length(rules, mass, StarAge.YOUNG) or 0
    main = stage_length(rules, mass, StarAge.MAIN) or 0
    old = stage_length(rules, mass, StarAge.OLD) or 0
    return {
        StarAge.YOUNG: 0,
        StarAge.MAIN: young,
        StarAge.OLD: young + main,
        StarAge.DYING: young + main + old,
        StarAge.DEAD: young + main + old + (stage_length(rules, mass, StarAge.DYING) or 0),
        StarAge.REBORN: 0,
    }[stage]


def band_of_light(rules: Rules, luminosity: float) -> tuple[float, float]:
    table = rules.stellar_evolution
    root = math.sqrt(max(0.0, luminosity))
    return hundredths(table.habitable_inner_hundredths) * root, hundredths(table.habitable_outer_hundredths) * root


def temperate_orbit(rules: Rules, star: StarRow, physics: StarPhysicsRow | None = None) -> float:
    if physics is not None:
        inner, outer = physics.band_inner, physics.band_outer
    else:
        inner, outer = band_of_light(rules, luminosity_of(rules, inferred_mass(rules, star), star.age_stage, star.star_type))
    return round((inner + outer) / 2, 4)


def target_brightness(rules: Rules, star_type: StarType, luminosity: float) -> int:
    table = rules.stellar_evolution
    value = table.sun_brightness + math.log10(max(luminosity, 1e-6)) * table.brightness_per_decade
    low, high = brightness_band(rules, star_type)
    return clamp_int(round_half_up(value), low, high)


def is_dwarf(rules: Rules, mass: float) -> bool:
    return mass < hundredths(rules.stellar_evolution.dwarf_mass_hundredths)


def ends_in_supernova(rules: Rules, mass: float) -> bool:
    return mass >= hundredths(rules.stellar_evolution.supernova_mass_hundredths)


def giant_for(rules: Rules, mass: float) -> StarType | None:
    if is_dwarf(rules, mass):
        return None
    return StarType.RED_SUPERGIANT if ends_in_supernova(rules, mass) else StarType.RED_GIANT


def remnant_for(rules: Rules, mass: float) -> StarType:
    if not ends_in_supernova(rules, mass):
        return StarType.WHITE_DWARF
    return StarType.BLACK_HOLE if mass >= hundredths(rules.stellar_evolution.black_hole_mass_hundredths) else StarType.NEUTRON_STAR


def engulf_orbit(rules: Rules, mass: float) -> float:
    return mass * rules.stellar_evolution.engulf_orbit_per_mass_pct / PERCENT


def inferred_mass(rules: Rules, star: StarRow) -> float:
    base = typical_mass(rules, star.star_type)
    low, high = brightness_band(rules, star.star_type)
    if high <= low or star.star_type in REMNANTS:
        return base
    lean = (star.brightness - (low + high) / 2) / (high - low)
    return max(0.01, base * (1 + lean / 2))


def inferred_age(rules: Rules, star: StarRow, mass: float) -> int:
    life = main_life(rules, mass)
    young = stage_length(rules, mass, StarAge.YOUNG) or 0
    return {
        StarAge.YOUNG: 0,
        StarAge.MAIN: young + life // 2,
        StarAge.OLD: young + life,
        StarAge.DYING: young + life + (stage_length(rules, mass, StarAge.OLD) or 0),
        StarAge.DEAD: young + life * 2,
        StarAge.REBORN: 0,
    }[star.age_stage]


def new_physics(rules: Rules, star: StarRow, galaxy: GalaxyRow | None) -> StarPhysicsRow:
    mass = inferred_mass(rules, star)
    luminosity = luminosity_of(rules, mass, star.age_stage, star.star_type)
    inner, outer = band_of_light(rules, luminosity)
    return StarPhysicsRow(
        star_id=star.id,
        mass=round(mass, 3),
        metallicity=clamp_percent(galaxy.metallicity if galaxy is not None else PERCENT // 2),
        age_epochs=inferred_age(rules, star, mass),
        luminosity=luminosity,
        lifetime_epochs=main_life(rules, mass),
        band_inner=inner,
        band_outer=outer,
        upkeep=0,
        locked=[],
    )


async def physics_of_stars(session: AsyncSession, rules: Rules, stars: list[StarRow]) -> dict[int, StarPhysicsRow]:
    found = {row.star_id: row for row in await session.scalars(select(StarPhysicsRow))}
    missing = [star for star in stars if star.id not in found]
    if missing:
        galaxies = {row.id: row for row in await session.scalars(select(GalaxyRow))}
        for star in missing:
            row = new_physics(rules, star, galaxies.get(star.galaxy_id) if star.galaxy_id is not None else None)
            session.add(row)
            found[star.id] = row
        await session.flush()
    return found


async def luminosity_shifts(session: AsyncSession) -> dict[int, int]:
    rows = await session.execute(select(StarModifierRow.star_id, func.sum(StarModifierRow.luminosity_pct)).group_by(StarModifierRow.star_id))
    return {star_id: int(total or 0) for star_id, total in rows}


def refresh(rules: Rules, star: StarRow, physics: StarPhysicsRow, shift_pct: int = 0) -> None:
    if "luminosity" not in physics.locked:
        base = luminosity_of(rules, physics.mass, star.age_stage, star.star_type)
        physics.luminosity = base * max(0, PERCENT + shift_pct) / PERCENT
    if "lifetime_epochs" not in physics.locked:
        physics.lifetime_epochs = main_life(rules, physics.mass)
    inner, outer = band_of_light(rules, physics.luminosity)
    if "band_inner" not in physics.locked:
        physics.band_inner = inner
    if "band_outer" not in physics.locked:
        physics.band_outer = outer


def drift_brightness(rules: Rules, star: StarRow, physics: StarPhysicsRow) -> None:
    if "brightness" in star.locked:
        return
    target = target_brightness(rules, star.star_type, physics.luminosity)
    step = rules.stellar_evolution.brightness_drift
    star.brightness = clamp_percent(star.brightness + max(-step, min(step, target - star.brightness)))


def drift_metallicity(rules: Rules, star: StarRow, physics: StarPhysicsRow, galaxy: GalaxyRow | None) -> None:
    if galaxy is None or star.age_stage is not StarAge.YOUNG or "metallicity" in physics.locked:
        return
    step = rules.stellar_evolution.metallicity_drift
    physics.metallicity = clamp_percent(physics.metallicity + max(-step, min(step, galaxy.metallicity - physics.metallicity)))
