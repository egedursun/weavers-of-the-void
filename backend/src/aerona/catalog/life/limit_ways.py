from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body_systems import LimitWay
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class LimitWaySpec:
    label: str
    ease: Callable[[Rules], int]
    cost: Callable[[Rules], int]


LIMIT_WAYS: Mapping[LimitWay, LimitWaySpec] = total(
    LimitWay,
    {
        LimitWay.EQUIPMENT: LimitWaySpec("Equipment", lambda rules: rules.body_systems.equipment_ease_pct, lambda rules: rules.body_systems.equipment_cost),
        LimitWay.AUGMENT: LimitWaySpec("Augments", lambda rules: rules.body_systems.augment_ease_pct, lambda rules: rules.body_systems.augment_cost),
        LimitWay.GROWN_ORGAN: LimitWaySpec("Grown organs", lambda rules: rules.body_systems.grown_ease_pct, lambda rules: rules.body_systems.grown_cost),
        LimitWay.POWER: LimitWaySpec("A power", lambda rules: rules.body_systems.power_ease_pct, lambda rules: rules.body_systems.power_cost),
        LimitWay.RITE: LimitWaySpec("A rite", lambda rules: rules.body_systems.rite_ease_pct, lambda rules: rules.body_systems.rite_cost),
    },
)
