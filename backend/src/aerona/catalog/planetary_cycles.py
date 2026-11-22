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
