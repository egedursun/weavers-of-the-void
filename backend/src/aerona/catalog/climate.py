from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.rules.registry import Rules

PERCENT = 100


@dataclass(frozen=True)
class ClimateSpec:
    era: ClimateEra
    label: str
    description: str
    temperature_shift: Callable[[Rules], int]
    rain_shift: Callable[[Rules], int]
    weight: Callable[[Rules], int]


@dataclass(frozen=True)
class ClimateProfile:
    era: ClimateEra
    label: str
    description: str
    temperature_shift: int
    rain_shift: int
    weight: int


CLIMATES: dict[ClimateEra, ClimateSpec] = {
    spec.era: spec
    for spec in (
        ClimateSpec(
            ClimateEra.TEMPERATE,
            "Temperate age",
            "The seasons keep their places.",
            lambda rules: rules.climate_effects.temperate_temperature,
            lambda rules: rules.climate_effects.temperate_rain,
            lambda rules: rules.climate_effects.temperate_weight,
        ),
        ClimateSpec(
            ClimateEra.DROUGHT,
            "Drought century",
            "Rivers recede and the interiors scorch.",
            lambda rules: rules.climate_effects.drought_century_temperature,
            lambda rules: rules.climate_effects.drought_century_rain,
            lambda rules: rules.climate_effects.drought_century_weight,
        ),
        ClimateSpec(
            ClimateEra.RAIN,
            "Rain age",
            "Rain without end: floods on the coasts, plenty in the plains.",
            lambda rules: rules.climate_effects.rain_age_temperature,
            lambda rules: rules.climate_effects.rain_age_rain,
            lambda rules: rules.climate_effects.rain_age_weight,
        ),
        ClimateSpec(
            ClimateEra.ICE_AGE,
            "Ice age",
            "Winters lengthen and mountain passes close.",
            lambda rules: rules.climate_effects.ice_age_temperature,
            lambda rules: rules.climate_effects.ice_age_rain,
            lambda rules: rules.climate_effects.ice_age_weight,
        ),
        ClimateSpec(
            ClimateEra.SCORCHING,
            "Scorching age",
            "The sun has lowered; disease and anger rise.",
            lambda rules: rules.climate_effects.scorching_age_temperature,
            lambda rules: rules.climate_effects.scorching_age_rain,
            lambda rules: rules.climate_effects.scorching_age_weight,
        ),
    )
}

WORLD_CLIMATE_MULTIPLIERS: dict[tuple[WorldType, ClimateEra], Callable[[Rules], int]] = {
    (WorldType.OCEAN, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.ocean_ice_age,
    (WorldType.OCEAN, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.ocean_drought,
    (WorldType.OCEAN, ClimateEra.RAIN): lambda rules: rules.climate_world_type.ocean_rain,
    (WorldType.SAND, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.sand_drought,
    (WorldType.SAND, ClimateEra.RAIN): lambda rules: rules.climate_world_type.sand_rain,
    (WorldType.SAND, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.sand_scorching,
    (WorldType.ICE, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.ice_ice_age,
    (WorldType.ICE, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.ice_scorching,
    (WorldType.ICE, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.ice_drought,
    (WorldType.LAVA, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.lava_scorching,
    (WorldType.LAVA, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.lava_ice_age,
    (WorldType.LAVA, ClimateEra.RAIN): lambda rules: rules.climate_world_type.lava_rain,
    (WorldType.GAS, ClimateEra.RAIN): lambda rules: rules.climate_world_type.gas_rain,
    (WorldType.DEAD, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.dead_temperate,
    (WorldType.DEAD, ClimateEra.RAIN): lambda rules: rules.climate_world_type.dead_rain,
    (WorldType.TIDALLY_LOCKED, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.tidally_locked_scorching,
    (WorldType.TIDALLY_LOCKED, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.tidally_locked_ice_age,
    (WorldType.TIDALLY_LOCKED, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.tidally_locked_temperate,
    (WorldType.GENERATION_SHIP, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.generation_ship_temperate,
    (WorldType.VOID_POCKET, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.void_pocket_temperate,
    (WorldType.CORPSE_WORLD, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.corpse_world_drought,
    (WorldType.CORPSE_WORLD, ClimateEra.RAIN): lambda rules: rules.climate_world_type.corpse_world_rain,
    (WorldType.LIVING, ClimateEra.RAIN): lambda rules: rules.climate_world_type.living_rain,
    (WorldType.CRYSTAL, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.crystal_ice_age,
    (WorldType.ASTEROID_BELT, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.asteroid_belt_drought,
    (WorldType.RINGED, ClimateEra.RAIN): lambda rules: rules.climate_world_type.ringed_rain,
    (WorldType.GODS_PALACE, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.gods_palace_temperate,
    (WorldType.FORGE, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.forge_scorching,
    (WorldType.FORGE, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.forge_drought,
    (WorldType.FORGE, ClimateEra.RAIN): lambda rules: rules.climate_world_type.forge_rain,
    (WorldType.SUPER_EARTH, ClimateEra.RAIN): lambda rules: rules.climate_world_type.super_earth_rain,
    (WorldType.ICE_GIANT, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.ice_giant_ice_age,
    (WorldType.ICE_GIANT, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.ice_giant_scorching,
    (WorldType.HOT_GIANT, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.hot_giant_scorching,
    (WorldType.HOT_GIANT, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.hot_giant_ice_age,
    (WorldType.IRON, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.iron_drought,
    (WorldType.IRON, ClimateEra.RAIN): lambda rules: rules.climate_world_type.iron_rain,
    (WorldType.CARBON, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.carbon_drought,
    (WorldType.GREENHOUSE, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.greenhouse_scorching,
    (WorldType.GREENHOUSE, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.greenhouse_ice_age,
    (WorldType.GREENHOUSE, ClimateEra.RAIN): lambda rules: rules.climate_world_type.greenhouse_rain,
    (WorldType.DWARF_PLANET, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.dwarf_planet_ice_age,
    (WorldType.DWARF_PLANET, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.dwarf_planet_scorching,
    (WorldType.CHTHONIAN, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.chthonian_scorching,
    (WorldType.CHTHONIAN, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.chthonian_ice_age,
    (WorldType.CHTHONIAN, ClimateEra.RAIN): lambda rules: rules.climate_world_type.chthonian_rain,
    (WorldType.HYCEAN, ClimateEra.RAIN): lambda rules: rules.climate_world_type.hycean_rain,
    (WorldType.HYCEAN, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.hycean_drought,
    (WorldType.JUNGLE, ClimateEra.RAIN): lambda rules: rules.climate_world_type.jungle_rain,
    (WorldType.JUNGLE, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.jungle_drought,
    (WorldType.FUNGAL, ClimateEra.RAIN): lambda rules: rules.climate_world_type.fungal_rain,
    (WorldType.FUNGAL, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.fungal_scorching,
    (WorldType.SHATTERED, ClimateEra.DROUGHT): lambda rules: rules.climate_world_type.shattered_drought,
    (WorldType.HOLLOW, ClimateEra.TEMPERATE): lambda rules: rules.climate_world_type.hollow_temperate,
    (WorldType.ICE_SHELL, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.ice_shell_ice_age,
    (WorldType.ICE_SHELL, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.ice_shell_scorching,
    (WorldType.METHANE, ClimateEra.RAIN): lambda rules: rules.climate_world_type.methane_rain,
    (WorldType.METHANE, ClimateEra.ICE_AGE): lambda rules: rules.climate_world_type.methane_ice_age,
    (WorldType.METHANE, ClimateEra.SCORCHING): lambda rules: rules.climate_world_type.methane_scorching,
}


def climate_profile(rules: Rules, era: ClimateEra) -> ClimateProfile:
    spec = CLIMATES[era]
    return ClimateProfile(era, spec.label, spec.description, spec.temperature_shift(rules), spec.rain_shift(rules), spec.weight(rules))


def climate_weight(rules: Rules, world_type: WorldType, era: ClimateEra) -> float:
    multiplier = WORLD_CLIMATE_MULTIPLIERS.get((world_type, era))
    percent = multiplier(rules) if multiplier is not None else PERCENT
    return percent / PERCENT * CLIMATES[era].weight(rules)


def climate_weights(rules: Rules, world_type: WorldType) -> dict[ClimateEra, float]:
    return {era: climate_weight(rules, world_type, era) for era in ClimateEra}
