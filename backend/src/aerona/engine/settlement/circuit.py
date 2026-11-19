from math import ceil, sqrt

from aerona.constants.units import PERCENT
from aerona.rules.registry import Rules


def circuit_towers(rules: Rules, population: int) -> int:
    return ceil(sqrt(max(0, population)) / rules.scale.tower_root)


def circuit_gates(rules: Rules, population: int) -> int:
    return max(1, ceil(circuit_towers(rules, population) / rules.scale.towers_per_gate))


def tower_defence(rules: Rules, towers: int, population: int) -> float:
    spacing = towers / max(1, circuit_towers(rules, population))
    return spacing * rules.scale.circuit_tower_weight * rules.districts.tower_defence_pct / PERCENT
