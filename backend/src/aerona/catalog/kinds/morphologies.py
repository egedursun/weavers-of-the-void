from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.urban import Morphology


@dataclass(frozen=True)
class MorphologySpec:
    fire_rule: str | None = None
    hauling_rule: str | None = None
    siege_rule: str | None = None


M = Morphology
MORPHOLOGIES: Mapping[Morphology, MorphologySpec] = total(
    Morphology,
    {
        M.ORGANIC: MorphologySpec(fire_rule="organic_fire_pct", hauling_rule="organic_hauling_pct"),
        M.PLANNED: MorphologySpec(fire_rule="planned_fire_pct", hauling_rule="planned_hauling_pct"),
        M.CONCENTRIC: MorphologySpec(siege_rule="concentric_siege"),
        M.GRID: MorphologySpec(fire_rule="grid_fire_pct", hauling_rule="grid_hauling_pct"),
        M.VERTICAL: MorphologySpec(fire_rule="vertical_fire_pct", hauling_rule="vertical_hauling_pct"),
        M.SPRAWL: MorphologySpec(fire_rule="sprawl_fire_pct", hauling_rule="sprawl_hauling_pct"),
    },
)
