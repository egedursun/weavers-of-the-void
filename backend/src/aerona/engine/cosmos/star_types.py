from collections.abc import Callable
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow
from aerona.domain.enums.world import StarType
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.rules.registry import Rules

RuleValue = Callable[[Rules], int]


def _zero(rules: Rules) -> int:
    return 0


@dataclass(frozen=True)
class StarTypeMechanics:
    star_type: StarType
    brightness_min: RuleValue
    brightness_max: RuleValue
    heat: RuleValue
    capacity_pct: RuleValue
    collapse_weight: RuleValue
    flare_weight: RuleValue
    eclipse_weight: RuleValue = _zero
    leak: RuleValue = _zero
    leak_repair: RuleValue = _zero
    sanity_erosion: RuleValue = _zero
    sail_danger: RuleValue = _zero
    instability: RuleValue = _zero


S = StarType

STAR_TYPE_MECHANICS: dict[StarType, StarTypeMechanics] = {
    mechanics.star_type: mechanics
    for mechanics in (
        StarTypeMechanics(
            S.YELLOW_DWARF,
            brightness_min=lambda rules: rules.star_types.yellow_dwarf_brightness_min,
            brightness_max=lambda rules: rules.star_types.yellow_dwarf_brightness_max,
            heat=lambda rules: rules.star_types.yellow_dwarf_heat,
            capacity_pct=lambda rules: rules.star_types.yellow_dwarf_capacity,
            collapse_weight=lambda rules: rules.star_types.yellow_dwarf_collapse_weight,
            flare_weight=lambda rules: rules.star_types.yellow_dwarf_flare_weight,
        ),
        StarTypeMechanics(
            S.BLUE_STAR,
            brightness_min=lambda rules: rules.star_types.blue_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.blue_star_brightness_max,
            heat=lambda rules: rules.star_types.blue_star_heat,
            capacity_pct=lambda rules: rules.star_types.blue_star_capacity,
            collapse_weight=lambda rules: rules.star_types.blue_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.blue_star_flare_weight,
        ),
        StarTypeMechanics(
            S.BLUE_WHITE_STAR,
            brightness_min=lambda rules: rules.star_types.blue_white_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.blue_white_star_brightness_max,
            heat=lambda rules: rules.star_types.blue_white_star_heat,
            capacity_pct=lambda rules: rules.star_types.blue_white_star_capacity,
            collapse_weight=lambda rules: rules.star_types.blue_white_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.blue_white_star_flare_weight,
        ),
        StarTypeMechanics(
            S.WHITE_STAR,
            brightness_min=lambda rules: rules.star_types.white_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.white_star_brightness_max,
            heat=lambda rules: rules.star_types.white_star_heat,
            capacity_pct=lambda rules: rules.star_types.white_star_capacity,
            collapse_weight=lambda rules: rules.star_types.white_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.white_star_flare_weight,
        ),
        StarTypeMechanics(
            S.YELLOW_WHITE_STAR,
            brightness_min=lambda rules: rules.star_types.yellow_white_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.yellow_white_star_brightness_max,
            heat=lambda rules: rules.star_types.yellow_white_star_heat,
            capacity_pct=lambda rules: rules.star_types.yellow_white_star_capacity,
            collapse_weight=lambda rules: rules.star_types.yellow_white_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.yellow_white_star_flare_weight,
        ),
        StarTypeMechanics(
            S.ORANGE_DWARF,
            brightness_min=lambda rules: rules.star_types.orange_dwarf_brightness_min,
            brightness_max=lambda rules: rules.star_types.orange_dwarf_brightness_max,
            heat=lambda rules: rules.star_types.orange_dwarf_heat,
            capacity_pct=lambda rules: rules.star_types.orange_dwarf_capacity,
            collapse_weight=lambda rules: rules.star_types.orange_dwarf_collapse_weight,
            flare_weight=lambda rules: rules.star_types.orange_dwarf_flare_weight,
        ),
        StarTypeMechanics(
            S.RED_DWARF,
            brightness_min=lambda rules: rules.star_types.red_dwarf_brightness_min,
            brightness_max=lambda rules: rules.star_types.red_dwarf_brightness_max,
            heat=lambda rules: rules.star_types.red_dwarf_heat,
            capacity_pct=lambda rules: rules.star_types.red_dwarf_capacity,
            collapse_weight=lambda rules: rules.star_types.red_dwarf_collapse_weight,
            flare_weight=lambda rules: rules.star_types.red_dwarf_flare_weight,
        ),
        StarTypeMechanics(
            S.BROWN_DWARF,
            brightness_min=lambda rules: rules.star_types.brown_dwarf_brightness_min,
            brightness_max=lambda rules: rules.star_types.brown_dwarf_brightness_max,
            heat=lambda rules: rules.star_types.brown_dwarf_heat,
            capacity_pct=lambda rules: rules.star_types.brown_dwarf_capacity,
            collapse_weight=lambda rules: rules.star_types.brown_dwarf_collapse_weight,
            flare_weight=lambda rules: rules.star_types.brown_dwarf_flare_weight,
        ),
        StarTypeMechanics(
            S.YELLOW_GIANT,
            brightness_min=lambda rules: rules.star_types.yellow_giant_brightness_min,
            brightness_max=lambda rules: rules.star_types.yellow_giant_brightness_max,
            heat=lambda rules: rules.star_types.yellow_giant_heat,
            capacity_pct=lambda rules: rules.star_types.yellow_giant_capacity,
            collapse_weight=lambda rules: rules.star_types.yellow_giant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.yellow_giant_flare_weight,
        ),
        StarTypeMechanics(
            S.RED_GIANT,
            brightness_min=lambda rules: rules.star_types.red_giant_brightness_min,
            brightness_max=lambda rules: rules.star_types.red_giant_brightness_max,
            heat=lambda rules: rules.star_types.red_giant_heat,
            capacity_pct=lambda rules: rules.star_types.red_giant_capacity,
            collapse_weight=lambda rules: rules.star_types.red_giant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.red_giant_flare_weight,
        ),
        StarTypeMechanics(
            S.BLUE_GIANT,
            brightness_min=lambda rules: rules.star_types.blue_giant_brightness_min,
            brightness_max=lambda rules: rules.star_types.blue_giant_brightness_max,
            heat=lambda rules: rules.star_types.blue_giant_heat,
            capacity_pct=lambda rules: rules.star_types.blue_giant_capacity,
            collapse_weight=lambda rules: rules.star_types.blue_giant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.blue_giant_flare_weight,
        ),
        StarTypeMechanics(
            S.RED_SUPERGIANT,
            brightness_min=lambda rules: rules.star_types.red_supergiant_brightness_min,
            brightness_max=lambda rules: rules.star_types.red_supergiant_brightness_max,
            heat=lambda rules: rules.star_types.red_supergiant_heat,
            capacity_pct=lambda rules: rules.star_types.red_supergiant_capacity,
            collapse_weight=lambda rules: rules.star_types.red_supergiant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.red_supergiant_flare_weight,
        ),
        StarTypeMechanics(
            S.BLUE_SUPERGIANT,
            brightness_min=lambda rules: rules.star_types.blue_supergiant_brightness_min,
            brightness_max=lambda rules: rules.star_types.blue_supergiant_brightness_max,
            heat=lambda rules: rules.star_types.blue_supergiant_heat,
            capacity_pct=lambda rules: rules.star_types.blue_supergiant_capacity,
            collapse_weight=lambda rules: rules.star_types.blue_supergiant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.blue_supergiant_flare_weight,
        ),
        StarTypeMechanics(
            S.HYPERGIANT,
            brightness_min=lambda rules: rules.star_types.hypergiant_brightness_min,
            brightness_max=lambda rules: rules.star_types.hypergiant_brightness_max,
            heat=lambda rules: rules.star_types.hypergiant_heat,
            capacity_pct=lambda rules: rules.star_types.hypergiant_capacity,
            collapse_weight=lambda rules: rules.star_types.hypergiant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.hypergiant_flare_weight,
            instability=lambda rules: rules.star_types.hypergiant_instability,
        ),
        StarTypeMechanics(
            S.WOLF_RAYET,
            brightness_min=lambda rules: rules.star_types.wolf_rayet_brightness_min,
            brightness_max=lambda rules: rules.star_types.wolf_rayet_brightness_max,
            heat=lambda rules: rules.star_types.wolf_rayet_heat,
            capacity_pct=lambda rules: rules.star_types.wolf_rayet_capacity,
            collapse_weight=lambda rules: rules.star_types.wolf_rayet_collapse_weight,
            flare_weight=lambda rules: rules.star_types.wolf_rayet_flare_weight,
            sail_danger=lambda rules: rules.star_types.wolf_rayet_sail_danger,
        ),
        StarTypeMechanics(
            S.PROTOSTAR,
            brightness_min=lambda rules: rules.star_types.protostar_brightness_min,
            brightness_max=lambda rules: rules.star_types.protostar_brightness_max,
            heat=lambda rules: rules.star_types.protostar_heat,
            capacity_pct=lambda rules: rules.star_types.protostar_capacity,
            collapse_weight=lambda rules: rules.star_types.protostar_collapse_weight,
            flare_weight=lambda rules: rules.star_types.protostar_flare_weight,
            sail_danger=lambda rules: rules.star_types.protostar_sail_danger,
            instability=lambda rules: rules.star_types.protostar_instability,
        ),
        StarTypeMechanics(
            S.CARBON_STAR,
            brightness_min=lambda rules: rules.star_types.carbon_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.carbon_star_brightness_max,
            heat=lambda rules: rules.star_types.carbon_star_heat,
            capacity_pct=lambda rules: rules.star_types.carbon_star_capacity,
            collapse_weight=lambda rules: rules.star_types.carbon_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.carbon_star_flare_weight,
        ),
        StarTypeMechanics(
            S.WHITE_DWARF,
            brightness_min=lambda rules: rules.star_types.white_dwarf_brightness_min,
            brightness_max=lambda rules: rules.star_types.white_dwarf_brightness_max,
            heat=lambda rules: rules.star_types.white_dwarf_heat,
            capacity_pct=lambda rules: rules.star_types.white_dwarf_capacity,
            collapse_weight=lambda rules: rules.star_types.white_dwarf_collapse_weight,
            flare_weight=lambda rules: rules.star_types.white_dwarf_flare_weight,
        ),
        StarTypeMechanics(
            S.BINARY,
            brightness_min=lambda rules: rules.star_types.binary_brightness_min,
            brightness_max=lambda rules: rules.star_types.binary_brightness_max,
            heat=lambda rules: rules.star_types.binary_heat,
            capacity_pct=lambda rules: rules.star_types.binary_capacity,
            collapse_weight=lambda rules: rules.star_types.binary_collapse_weight,
            flare_weight=lambda rules: rules.star_types.binary_flare_weight,
            eclipse_weight=lambda rules: rules.star_types.binary_eclipse_weight,
        ),
        StarTypeMechanics(
            S.TRINARY,
            brightness_min=lambda rules: rules.star_types.trinary_brightness_min,
            brightness_max=lambda rules: rules.star_types.trinary_brightness_max,
            heat=lambda rules: rules.star_types.trinary_heat,
            capacity_pct=lambda rules: rules.star_types.trinary_capacity,
            collapse_weight=lambda rules: rules.star_types.trinary_collapse_weight,
            flare_weight=lambda rules: rules.star_types.trinary_flare_weight,
            eclipse_weight=lambda rules: rules.star_types.trinary_eclipse_weight,
            instability=lambda rules: rules.star_types.trinary_instability,
        ),
        StarTypeMechanics(
            S.VARIABLE_STAR,
            brightness_min=lambda rules: rules.star_types.variable_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.variable_star_brightness_max,
            heat=lambda rules: rules.star_types.variable_star_heat,
            capacity_pct=lambda rules: rules.star_types.variable_star_capacity,
            collapse_weight=lambda rules: rules.star_types.variable_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.variable_star_flare_weight,
            instability=lambda rules: rules.star_types.variable_star_instability,
        ),
        StarTypeMechanics(
            S.NEUTRON_STAR,
            brightness_min=lambda rules: rules.star_types.neutron_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.neutron_star_brightness_max,
            heat=lambda rules: rules.star_types.neutron_star_heat,
            capacity_pct=lambda rules: rules.star_types.neutron_star_capacity,
            collapse_weight=lambda rules: rules.star_types.neutron_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.neutron_star_flare_weight,
            sail_danger=lambda rules: rules.star_types.neutron_star_sail_danger,
        ),
        StarTypeMechanics(
            S.PULSAR,
            brightness_min=lambda rules: rules.star_types.pulsar_brightness_min,
            brightness_max=lambda rules: rules.star_types.pulsar_brightness_max,
            heat=lambda rules: rules.star_types.pulsar_heat,
            capacity_pct=lambda rules: rules.star_types.pulsar_capacity,
            collapse_weight=lambda rules: rules.star_types.pulsar_collapse_weight,
            flare_weight=lambda rules: rules.star_types.pulsar_flare_weight,
            sail_danger=lambda rules: rules.star_types.pulsar_sail_danger,
        ),
        StarTypeMechanics(
            S.MAGNETAR,
            brightness_min=lambda rules: rules.star_types.magnetar_brightness_min,
            brightness_max=lambda rules: rules.star_types.magnetar_brightness_max,
            heat=lambda rules: rules.star_types.magnetar_heat,
            capacity_pct=lambda rules: rules.star_types.magnetar_capacity,
            collapse_weight=lambda rules: rules.star_types.magnetar_collapse_weight,
            flare_weight=lambda rules: rules.star_types.magnetar_flare_weight,
            sanity_erosion=lambda rules: rules.star_types.magnetar_sanity_erosion,
            sail_danger=lambda rules: rules.star_types.magnetar_sail_danger,
        ),
        StarTypeMechanics(
            S.BLACK_HOLE,
            brightness_min=lambda rules: rules.star_types.black_hole_brightness_min,
            brightness_max=lambda rules: rules.star_types.black_hole_brightness_max,
            heat=lambda rules: rules.star_types.black_hole_heat,
            capacity_pct=lambda rules: rules.star_types.black_hole_capacity,
            collapse_weight=lambda rules: rules.star_types.black_hole_collapse_weight,
            flare_weight=lambda rules: rules.star_types.black_hole_flare_weight,
            sail_danger=lambda rules: rules.star_types.black_hole_sail_danger,
        ),
        StarTypeMechanics(
            S.DEAD_STAR,
            brightness_min=lambda rules: rules.star_types.dead_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.dead_star_brightness_max,
            heat=lambda rules: rules.star_types.dead_star_heat,
            capacity_pct=lambda rules: rules.star_types.dead_star_capacity,
            collapse_weight=lambda rules: rules.star_types.dead_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.dead_star_flare_weight,
        ),
        StarTypeMechanics(
            S.BLACK_SUN,
            brightness_min=lambda rules: rules.star_types.black_sun_brightness_min,
            brightness_max=lambda rules: rules.star_types.black_sun_brightness_max,
            heat=lambda rules: rules.star_types.black_sun_heat,
            capacity_pct=lambda rules: rules.star_types.black_sun_capacity,
            collapse_weight=lambda rules: rules.star_types.black_sun_collapse_weight,
            flare_weight=lambda rules: rules.star_types.black_sun_flare_weight,
            sanity_erosion=lambda rules: rules.star_types.black_sun_sanity_erosion,
        ),
        StarTypeMechanics(
            S.BROKEN_STAR,
            brightness_min=lambda rules: rules.star_types.broken_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.broken_star_brightness_max,
            heat=lambda rules: rules.star_types.broken_star_heat,
            capacity_pct=lambda rules: rules.star_types.broken_star_capacity,
            collapse_weight=lambda rules: rules.star_types.broken_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.broken_star_flare_weight,
        ),
        StarTypeMechanics(
            S.STAR_REMNANT,
            brightness_min=lambda rules: rules.star_types.star_remnant_brightness_min,
            brightness_max=lambda rules: rules.star_types.star_remnant_brightness_max,
            heat=lambda rules: rules.star_types.star_remnant_heat,
            capacity_pct=lambda rules: rules.star_types.star_remnant_capacity,
            collapse_weight=lambda rules: rules.star_types.star_remnant_collapse_weight,
            flare_weight=lambda rules: rules.star_types.star_remnant_flare_weight,
            sail_danger=lambda rules: rules.star_types.star_remnant_sail_danger,
        ),
        StarTypeMechanics(
            S.REBORN_STAR,
            brightness_min=lambda rules: rules.star_types.reborn_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.reborn_star_brightness_max,
            heat=lambda rules: rules.star_types.reborn_star_heat,
            capacity_pct=lambda rules: rules.star_types.reborn_star_capacity,
            collapse_weight=lambda rules: rules.star_types.reborn_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.reborn_star_flare_weight,
        ),
        StarTypeMechanics(
            S.CHAINED_STAR,
            brightness_min=lambda rules: rules.star_types.chained_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.chained_star_brightness_max,
            heat=lambda rules: rules.star_types.chained_star_heat,
            capacity_pct=lambda rules: rules.star_types.chained_star_capacity,
            collapse_weight=lambda rules: rules.star_types.chained_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.chained_star_flare_weight,
            leak_repair=lambda rules: rules.star_types.chained_star_leak_repair,
        ),
        StarTypeMechanics(
            S.WATCHING_STAR,
            brightness_min=lambda rules: rules.star_types.watching_star_brightness_min,
            brightness_max=lambda rules: rules.star_types.watching_star_brightness_max,
            heat=lambda rules: rules.star_types.watching_star_heat,
            capacity_pct=lambda rules: rules.star_types.watching_star_capacity,
            collapse_weight=lambda rules: rules.star_types.watching_star_collapse_weight,
            flare_weight=lambda rules: rules.star_types.watching_star_flare_weight,
            leak=lambda rules: rules.star_types.watching_star_leak,
            sanity_erosion=lambda rules: rules.star_types.watching_star_sanity_erosion,
        ),
    )
}


def star_mechanics(star_type: StarType) -> StarTypeMechanics:
    return STAR_TYPE_MECHANICS[star_type]


def brightness_band(rules: Rules, star_type: StarType) -> tuple[int, int]:
    mechanics = star_mechanics(star_type)
    low, high = mechanics.brightness_min(rules), mechanics.brightness_max(rules)
    return min(low, high), max(low, high)


def kindled_brightness(rules: Rules, star_type: StarType, roll_pct: int) -> int:
    low, high = brightness_band(rules, star_type)
    return low + round_half_up((high - low) * clamp_percent(roll_pct) / PERCENT)


def fitted_brightness(rules: Rules, star_type: StarType, brightness: int) -> int:
    low, high = brightness_band(rules, star_type)
    return clamp_int(brightness, low, high)


def star_heat(rules: Rules, star: StarRow | None) -> int:
    if star is None:
        return 0
    low, high = brightness_band(rules, star.star_type)
    glow = (star.brightness - (low + high) / 2) * rules.star_types.brightness_heat_pct / PERCENT
    return round_half_up(star_mechanics(star.star_type).heat(rules) + glow)


def star_capacity_pct(rules: Rules, star: StarRow | None) -> int:
    return star_mechanics(star.star_type).capacity_pct(rules) if star is not None else PERCENT


def rekindle_cost(rules: Rules, star_type: StarType, base: int) -> int:
    table = rules.star_life
    pct = {
        StarType.BLACK_SUN: table.rekindle_dark_pct,
        StarType.BROKEN_STAR: table.rekindle_dark_pct,
        StarType.BLACK_HOLE: table.rekindle_remnant_pct,
        StarType.STAR_REMNANT: table.rekindle_remnant_pct,
    }.get(star_type, PERCENT)
    return round_half_up(base * pct / PERCENT)
