from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.evolution import CycleEffect

CYCLE_EFFECT = total(
    CycleEffect,
    {
        CycleEffect.GREENHOUSE: Defined("Greenhouse", checked_by=(), used_by=("catalog.planetary_cycles.CYCLES", "engine.cosmos.planetary.move_carbon")),
        CycleEffect.RAIN: Defined("Rain", checked_by=(), used_by=("catalog.planetary_cycles.CYCLES", "engine.cosmos.cycles.rain_swing")),
        CycleEffect.SEA_LEVEL: Defined(
            "Sea level", checked_by=("catalog.planetary_cycles.cycle_label",), used_by=("catalog.planetary_cycles.CYCLES", "engine.cosmos.cycles.raise_seas")
        ),
        CycleEffect.SOIL: Defined("Soil", checked_by=(), used_by=("catalog.planetary_cycles.CYCLES", "engine.cosmos.cycles.soil_swing")),
        CycleEffect.BREATH: Defined("Breath", checked_by=(), used_by=("catalog.planetary_cycles.CYCLES", "engine.cosmos.cycles.thin_air")),
    },
)
