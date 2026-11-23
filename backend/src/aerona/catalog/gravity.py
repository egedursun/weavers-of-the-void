from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.domain.enums.world import Gravity
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class GravitySpec:
    label: str
    g: float
    body: int
    strain: Callable[[Rules], int]
    martial: Callable[[Rules], int]
    speed: Callable[[Rules], int]
    build: Callable[[Rules], int]
    flight: Callable[[Rules], int]
    launch: int


GRAVITY: Mapping[Gravity, GravitySpec] = total(
    Gravity,
    {
        Gravity.MICRO: GravitySpec(
            "Micro",
            0.05,
            5,
            lambda rules: rules.physics.micro_body_strain,
            lambda rules: rules.physics.micro_martiality,
            lambda rules: PERCENT + rules.physics.micro_speed_pct,
            lambda rules: PERCENT,
            lambda rules: PERCENT + rules.physics.micro_flight_pct,
            -1,
        ),
        Gravity.LOW: GravitySpec(
            "Low",
            0.4,
            25,
            lambda rules: rules.physics.low_body_strain,
            lambda rules: rules.world_physics.martiality_low_gravity,
            lambda rules: PERCENT + rules.world_life.low_gravity_speed_pct,
            lambda rules: PERCENT,
            lambda rules: PERCENT + rules.world_life.low_gravity_flight_pct,
            0,
        ),
        Gravity.NORMAL: GravitySpec(
            "Normal",
            1.0,
            50,
            lambda rules: rules.physics.normal_body_strain,
            lambda rules: rules.world_physics.martiality_normal_gravity,
            lambda rules: PERCENT,
            lambda rules: PERCENT,
            lambda rules: PERCENT,
            0,
        ),
        Gravity.HIGH: GravitySpec(
            "High",
            1.8,
            80,
            lambda rules: rules.physics.high_body_strain,
            lambda rules: rules.world_physics.martiality_high_gravity,
            lambda rules: PERCENT - rules.world_life.high_gravity_speed_pct,
            lambda rules: PERCENT + rules.world_life.high_gravity_build_pct,
            lambda rules: PERCENT,
            0,
        ),
        Gravity.CRUSHING: GravitySpec(
            "Crushing",
            3.5,
            95,
            lambda rules: rules.physics.crushing_body_strain,
            lambda rules: rules.physics.crushing_martiality,
            lambda rules: max(0, PERCENT - rules.physics.crushing_speed_pct),
            lambda rules: PERCENT + rules.physics.crushing_build_pct,
            lambda rules: max(0, PERCENT - rules.physics.crushing_flight_pct),
            1,
        ),
    },
)

GRAVITY_ORDER: tuple[Gravity, ...] = tuple(sorted(GRAVITY, key=lambda band: GRAVITY[band].g))
