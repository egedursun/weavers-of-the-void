from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.evolution import CycleEffect, CycleSource, PlanetaryCycle
from aerona.domain.enums.world import SurfaceLiquid
from aerona.rules.registry import Rules

S = CycleSource
Rate = Callable[[Rules], int]


@dataclass(frozen=True)
class CycleFlow:
    source: CycleSource
    rate: Rate


@dataclass(frozen=True)
class CycleSpec:
    label: str
    sources: tuple[CycleFlow, ...]
    sinks: tuple[CycleFlow, ...]
    moves: frozenset[CycleEffect]
    seeded_by: frozenset[CycleSource] = frozenset()


CYCLES: Mapping[PlanetaryCycle, CycleSpec] = total(
    PlanetaryCycle,
    {
        PlanetaryCycle.CARBON: CycleSpec(
            "Carbon",
            (
                CycleFlow(S.VOLCANOES, lambda rules: rules.world_cycles.volcanic_carbon),
                CycleFlow(S.FIRES, lambda rules: rules.world_cycles.burning_carbon),
                CycleFlow(S.LIFE, lambda rules: rules.world_cycles.respiration),
            ),
            (
                CycleFlow(S.FORESTS, lambda rules: rules.world_cycles.forest_uptake),
                CycleFlow(S.OCEANS, lambda rules: rules.world_cycles.ocean_uptake),
                CycleFlow(S.WEATHERING, lambda rules: rules.world_cycles.weathering),
            ),
            frozenset({CycleEffect.GREENHOUSE}),
        ),
        PlanetaryCycle.WATER: CycleSpec(
            "Water",
            (
                CycleFlow(S.MELTING, lambda rules: rules.world_cycles.water_from_heat),
                CycleFlow(S.EVAPORATION, lambda rules: rules.world_cycles.evaporation),
            ),
            (
                CycleFlow(S.FREEZING, lambda rules: rules.world_cycles.water_from_heat),
                CycleFlow(S.RIVERS, lambda rules: rules.world_cycles.discharge),
            ),
            frozenset({CycleEffect.RAIN, CycleEffect.SEA_LEVEL}),
        ),
        PlanetaryCycle.NUTRIENTS: CycleSpec(
            "Nutrients",
            (
                CycleFlow(S.VOLCANOES, lambda rules: rules.world_cycles.ash_gain),
                CycleFlow(S.RIVERS, lambda rules: rules.world_cycles.river_gain),
            ),
            (CycleFlow(S.EROSION, lambda rules: rules.world_cycles.erosion_loss),),
            frozenset({CycleEffect.SOIL}),
        ),
        PlanetaryCycle.OXYGEN: CycleSpec(
            "Breathable air",
            (
                CycleFlow(S.FORESTS, lambda rules: rules.world_cycles.forest_oxygen),
                CycleFlow(S.OCEANS, lambda rules: rules.world_cycles.plankton_oxygen),
            ),
            (
                CycleFlow(S.FIRES, lambda rules: rules.cycles.oxygen_fire_draw),
                CycleFlow(S.LIFE, lambda rules: rules.world_cycles.respiration_oxygen),
                CycleFlow(S.WEATHERING, lambda rules: rules.world_cycles.weathering_oxygen),
                CycleFlow(S.INDUSTRY, lambda rules: rules.world_cycles.industry_oxygen),
            ),
            frozenset({CycleEffect.BREATH}),
            frozenset({S.FORESTS, S.OCEANS}),
        ),
        PlanetaryCycle.ROCK: CycleSpec(
            "Rock",
            (
                CycleFlow(S.VOLCANOES, lambda rules: rules.cycles.rock_volcanic_gain),
                CycleFlow(S.UPLIFT, lambda rules: rules.world_cycles.uplift_rock),
                CycleFlow(S.BURIAL, lambda rules: rules.world_cycles.burial_rock),
            ),
            (
                CycleFlow(S.WEATHERING, lambda rules: rules.cycles.rock_weathering_pct),
                CycleFlow(S.EROSION, lambda rules: rules.world_cycles.erosion_rock),
            ),
            frozenset({CycleEffect.SOIL}),
            frozenset({S.VOLCANOES, S.UPLIFT, S.WEATHERING}),
        ),
    },
)
SCALES: Mapping[PlanetaryCycle, tuple[Rate, Rate]] = total(
    PlanetaryCycle,
    {
        PlanetaryCycle.CARBON: (lambda rules: rules.cycles.carbon_source_pct, lambda rules: rules.cycles.carbon_sink_pct),
        PlanetaryCycle.WATER: (lambda rules: rules.cycles.water_source_pct, lambda rules: rules.cycles.water_sink_pct),
        PlanetaryCycle.NUTRIENTS: (lambda rules: rules.cycles.nutrients_source_pct, lambda rules: rules.cycles.nutrients_sink_pct),
        PlanetaryCycle.OXYGEN: (lambda rules: rules.cycles.oxygen_source_pct, lambda rules: rules.cycles.oxygen_sink_pct),
        PlanetaryCycle.ROCK: (lambda rules: rules.cycles.rock_source_pct, lambda rules: rules.cycles.rock_sink_pct),
    },
)

SOURCE_LABELS: Mapping[CycleSource, str] = total(
    CycleSource,
    {
        S.VOLCANOES: "Volcanoes",
        S.FIRES: "Fires and clearing",
        S.LIFE: "Breath and decay of animals",
        S.FORESTS: "Forests",
        S.OCEANS: "Oceans",
        S.WEATHERING: "Weathering rock",
        S.MELTING: "Warmth freeing ice",
        S.EVAPORATION: "Warm seas",
        S.FREEZING: "Cold binding ice",
        S.RIVERS: "Rivers",
        S.EROSION: "Erosion",
        S.INDUSTRY: "Foul air of industry",
        S.UPLIFT: "Mountain building",
        S.BURIAL: "Sediment buried deep",
    },
)

LIQUID_LABELS: Mapping[SurfaceLiquid, str] = total(
    SurfaceLiquid,
    {
        SurfaceLiquid.WATER: "Water",
        SurfaceLiquid.METHANE: "Methane",
        SurfaceLiquid.MOLTEN_ROCK: "Molten rock",
        SurfaceLiquid.NONE: "Volatiles",
    },
)


def cycles_moving(effect: CycleEffect) -> tuple[PlanetaryCycle, ...]:
    return tuple(cycle for cycle, spec in CYCLES.items() if effect in spec.moves)


def cycle_label(cycle: PlanetaryCycle, liquid: SurfaceLiquid) -> str:
    return LIQUID_LABELS[liquid] if CycleEffect.SEA_LEVEL in CYCLES[cycle].moves else CYCLES[cycle].label
