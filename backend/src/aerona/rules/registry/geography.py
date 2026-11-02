from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.EXPLORATION


@dataclass(frozen=True)
class GeographyRules:
    seed_cap: int = rule(3, 0, 100, G, "Most places born in empty regions per epoch")
    seed_chance: int = rule(35, 0, 100, G, "Chance that a place is born in a region without any place this epoch (%; doubled where a community lives)")
    move_chance: int = rule(50, 0, 100, G, "Chance that the most crowded settlement standing directly in the region moves to the new place's edge (%)")
    place_power: int = rule(2, 1, 12, G, "Power level of a place born in an empty region")
    fertile_threshold: int = rule(55, 0, 100, G, "Regions of this fertility or more bear fertile places (forest, lake, valley)")
    dangerous_threshold: int = rule(55, 0, 100, G, "Regions of this danger or more bear dangerous places (cave, marsh, pass)")
    magical_threshold: int = rule(55, 0, 100, G, "Regions of this magic or more bear magical places (well, stone circle)")
    stat_shift: int = rule(15, 0, 100, G, "Shift of a born place's fertility, danger or mystery toward its nature")
    place_stat: int = rule(50, 0, 100, G, "Base fertility, danger and mystery of a place born in an empty region")
    place_stat_die: int = rule(30, 1, 100, G, "Stat swing of a place born in an empty region (plus or minus half of this)")
    terrain_nature_weight: int = rule(2, 0, 100, G, "How many times more likely a place is to match its region's terrain")
