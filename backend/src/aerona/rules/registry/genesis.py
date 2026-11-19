from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class GenesisRules:
    regions_min: int = rule(3, 1, 50, RuleGroup.GENESIS, "Minimum regions at genesis")
    regions_max: int = rule(5, 1, 1000, RuleGroup.GENESIS, "Maximum regions at genesis")
    region_breadth: int = rule(60, 0, 100, RuleGroup.GENESIS, "Breadth of the initial regions")
    region_power: int = rule(8, 1, 11, RuleGroup.GENESIS, "Power level of the initial regions")
    sky_brightness: int = rule(70, 0, 100, RuleGroup.GENESIS, "Brightness of the first celestial body")
    sky_influence: int = rule(60, 0, 100, RuleGroup.GENESIS, "Influence of the first celestial body")
    sky_power: int = rule(7, 1, 11, RuleGroup.GENESIS, "Power level of the first celestial body")
    initial_son_relation: int = rule(80, 0, 100, RuleGroup.GENESIS, "Maximum magnitude (\u00b1) of the starting relation between the first sons")
    timeout: int = rule(360, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Genesis timeout (s)")
