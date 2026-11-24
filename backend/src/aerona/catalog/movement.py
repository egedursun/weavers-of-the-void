from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan
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
        M.SUBMERGED: MovementSpec(MovementMedium.UNDER_WATER, frozenset({MovementWork.HARBOURS}), lambda rules: (0, 0, 0, 0, 0), carries_trade=True),
        M.INCORPOREAL: MovementSpec(MovementMedium.THROUGH_MATTER, frozenset(), lambda rules: (0, 0, 0, 0, 0), carries_trade=False),
        M.SWIMMING: MovementSpec(
            MovementMedium.WATER_SURFACE, frozenset(), lambda rules: (0, 0, 0, 0, rules.passability.swimming_cold_pct), carries_trade=False
        ),
        M.CLIMBING: MovementSpec(
            MovementMedium.GROUND,
            frozenset({MovementWork.ROADS}),
            lambda rules: (
                rules.passability.climbing_roughness_pct,
                rules.passability.climbing_forest_pct,
                rules.passability.foot_wetland_pct,
                rules.passability.foot_river_pct,
                rules.passability.foot_cold_pct,
            ),
            carries_trade=False,
        ),
    },
)


def by_water(mode: str) -> bool:
    return MOVEMENT[MovementMode(mode)].medium is MovementMedium.WATER_SURFACE


def trade_modes() -> tuple[MovementMode, ...]:
    return tuple(mode for mode, spec in MOVEMENT.items() if spec.carries_trade)


FOOT = frozenset({M.ON_FOOT})
SPIRIT_WAYS = frozenset({M.INCORPOREAL})
ROCK_WAYS = frozenset({M.BURROWING, M.INCORPOREAL})
SOAKED_WAYS = frozenset({M.SUBMERGED, M.INCORPOREAL})
SEA_WAYS = frozenset({M.SUBMERGED, M.SWIMMING, M.BOAT, M.INCORPOREAL})
CAVE_WAYS = frozenset(mode for mode, spec in MOVEMENT.items() if spec.medium in {MovementMedium.GROUND, MovementMedium.AIR} or mode is M.INCORPOREAL)
UNDERWORLD_WAYS = frozenset({M.ON_FOOT, M.FLYING, M.INCORPOREAL})
NARROW_WAYS = frozenset({M.ON_FOOT, M.CLIMBING, M.BURROWING, M.SWIMMING, M.SUBMERGED, M.INCORPOREAL})
FLOODED_WAYS = frozenset({M.SUBMERGED, M.SWIMMING, M.INCORPOREAL})
EVERY_WAY = frozenset(MovementMode)
FOOT_WAYS = FOOT


def breathes_under_water(plan: BodyPlan) -> bool:
    return M.SUBMERGED in BODY_MODES[plan]


BODY_MODES: Mapping[BodyPlan, frozenset[MovementMode]] = total(
    BodyPlan,
    {
        BodyPlan.HUMANOID: frozenset({M.ON_FOOT, M.SWIMMING, M.CLIMBING}),
        BodyPlan.QUADRUPED: frozenset({M.ON_FOOT, M.SWIMMING}),
        BodyPlan.AVIAN: frozenset({M.ON_FOOT, M.FLYING}),
        BodyPlan.SERPENTINE: frozenset({M.ON_FOOT, M.SWIMMING, M.CLIMBING}),
        BodyPlan.INSECTOID: frozenset({M.ON_FOOT, M.BURROWING, M.CLIMBING}),
        BodyPlan.AQUATIC: frozenset({M.SUBMERGED, M.SWIMMING, M.ON_FOOT}),
        BodyPlan.AMORPHOUS: frozenset({M.ON_FOOT, M.SWIMMING, M.BURROWING}),
        BodyPlan.ARBOREAL: frozenset({M.ON_FOOT, M.CLIMBING}),
        BodyPlan.INCORPOREAL: frozenset({M.INCORPOREAL, M.FLYING}),
        BodyPlan.COLOSSAL: frozenset({M.ON_FOOT}),
        BodyPlan.CONSTRUCT: frozenset({M.ON_FOOT, M.WHEELED}),
        BodyPlan.DIVINE_MANIFEST: frozenset({M.ON_FOOT, M.FLYING}),
        BodyPlan.TENTACLED: frozenset({M.SUBMERGED, M.SWIMMING, M.CLIMBING}),
        BodyPlan.CENTAUROID: frozenset({M.ON_FOOT, M.SWIMMING}),
        BodyPlan.RADIAL: frozenset({M.SUBMERGED, M.ON_FOOT}),
        BodyPlan.COLONIAL: frozenset({M.SWIMMING, M.SUBMERGED, M.ON_FOOT}),
        BodyPlan.HEXAPOD: frozenset({M.ON_FOOT, M.CLIMBING}),
        BodyPlan.ROOTED: frozenset({M.ON_FOOT}),
    },
)


def best_passage(passability: Mapping[str, int], modes: frozenset[MovementMode], default: int) -> int:
    return max((passability.get(mode.value, default) for mode in sorted(modes)), default=default)


SPEED: Mapping[MovementMode, Callable[[Rules], int]] = total(
    MovementMode,
    {
        M.ON_FOOT: lambda rules: rules.movement.on_foot_speed,
        M.MOUNTED: lambda rules: rules.movement.mounted_speed,
        M.WHEELED: lambda rules: rules.movement.wheeled_speed,
        M.BOAT: lambda rules: rules.movement.boat_speed,
        M.FLYING: lambda rules: rules.movement.flying_speed,
        M.BURROWING: lambda rules: rules.movement.burrowing_speed,
        M.SUBMERGED: lambda rules: rules.movement.submerged_speed,
        M.INCORPOREAL: lambda rules: rules.movement.incorporeal_speed,
        M.SWIMMING: lambda rules: rules.movement.swimming_speed,
        M.CLIMBING: lambda rules: rules.movement.climbing_speed,
    },
)


def mode_through(passability: Mapping[str, int], modes: frozenset[MovementMode], default: int) -> MovementMode:
    return max(sorted(modes or FOOT), key=lambda mode: passability.get(mode.value, default))


def fastest(rules: Rules, modes: frozenset[MovementMode]) -> int:
    return max((SPEED[mode](rules) for mode in sorted(modes)), default=rules.movement.on_foot_speed)
