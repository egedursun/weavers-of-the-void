from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import MovementMedium, MovementMode, MovementWork
from aerona.rules.registry import Rules

M = MovementMode
Sensitivity = Callable[[Rules], tuple[int, int, int, int, int]]


@dataclass(frozen=True)
class MovementSpec:
    medium: MovementMedium
    works: frozenset[MovementWork]
    sensitivity: Sensitivity
    carries_trade: bool

    def takes(self, work: MovementWork) -> bool:
        return work in self.works


MOVEMENT: Mapping[MovementMode, MovementSpec] = total(
    MovementMode,
    {
        M.ON_FOOT: MovementSpec(
            MovementMedium.GROUND,
            frozenset({MovementWork.ROADS, MovementWork.BRIDGES}),
            lambda rules: (
                rules.passability.foot_roughness_pct,
                rules.passability.foot_forest_pct,
                rules.passability.foot_wetland_pct,
                rules.passability.foot_river_pct,
                rules.passability.foot_cold_pct,
            ),
            carries_trade=True,
        ),
        M.MOUNTED: MovementSpec(
            MovementMedium.GROUND,
            frozenset({MovementWork.ROADS, MovementWork.BRIDGES}),
            lambda rules: (
                rules.passability.mounted_roughness_pct,
                rules.passability.mounted_forest_pct,
                rules.passability.mounted_wetland_pct,
                rules.passability.mounted_river_pct,
                rules.passability.mounted_cold_pct,
            ),
            carries_trade=False,
        ),
        M.WHEELED: MovementSpec(
            MovementMedium.GROUND,
            frozenset({MovementWork.ROADS, MovementWork.BRIDGES}),
            lambda rules: (
                rules.passability.wheeled_roughness_pct,
                rules.passability.wheeled_forest_pct,
                rules.passability.wheeled_wetland_pct,
                rules.passability.wheeled_river_pct,
                rules.passability.wheeled_cold_pct,
            ),
            carries_trade=True,
        ),
        M.BOAT: MovementSpec(MovementMedium.WATER_SURFACE, frozenset({MovementWork.HARBOURS}), lambda rules: (0, 0, 0, 0, 0), carries_trade=True),
        M.FLYING: MovementSpec(MovementMedium.AIR, frozenset(), lambda rules: (rules.passability.flying_roughness_pct, 0, 0, 0, 0), carries_trade=False),
        M.BURROWING: MovementSpec(
            MovementMedium.THROUGH_MATTER,
            frozenset(),
            lambda rules: (
                rules.passability.burrowing_roughness_pct,
                0,
                rules.passability.burrowing_wetland_pct,
                rules.passability.burrowing_river_pct,
                rules.passability.burrowing_cold_pct,
            ),
            carries_trade=False,
        ),
    },
)


def by_water(mode: str) -> bool:
    return MOVEMENT[MovementMode(mode)].medium is MovementMedium.WATER_SURFACE


def trade_modes() -> tuple[MovementMode, ...]:
    return tuple(mode for mode, spec in MOVEMENT.items() if spec.carries_trade)
