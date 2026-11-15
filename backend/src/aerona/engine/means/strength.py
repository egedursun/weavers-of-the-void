from aerona.constants.units import PERCENT
from aerona.domain.enums.integrity import HarmForce
from aerona.engine.economy.materials import MaterialProps
from aerona.rules.registry import Rules


def siege_guard(rules: Rules, props: MaterialProps | None, force: HarmForce) -> float:
    if force is not HarmForce.SIEGE or props is None:
        return 1.0
    return 1 - props.hardness * rules.building_materials.siege_pct / PERCENT / PERCENT


def fire_loss(rules: Rules, props: MaterialProps | None, gale: float) -> float:
    ignition = props.ignition_point if props is not None else PERCENT // 2
    return rules.building_materials.fire_harm * (PERCENT - ignition) / PERCENT * gale
