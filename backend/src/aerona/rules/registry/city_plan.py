from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class CityPlanRules:
    cells_per_level: int = rule(1, 1, 6, S, "Hexes of the city plan each level of a district covers")
    ring_spacing: int = rule(2, 1, 6, S, "Hexes between the rings of the city plan's zones, from the seat of government outward")
    household: int = rule(5, 1, 50, S, "People living in one dwelling of a district")
    residential_housing_pct: int = rule(160, 0, 400, S, "Homes a residential quarter holds against another district of its level (%)")
    civic_quarter_at: int = rule(
        3, 1, 20, S, "Schools, healers, arenas, theatres, libraries and almshouses a town needs before it gathers them into a civic quarter"
    )
    gardens_prosperity: int = rule(60, 0, 100, S, "Prosperity a town with parks or fountains needs before it lays out gardens")
    garden_amenity: int = rule(10, 0, 100, S, "Desirability gardens give the districts near them")
    civic_reach_pct: int = rule(120, 100, 300, S, "How much further a service in the civic quarter reaches, against a service elsewhere (%)")
    almshouse_shelter: int = rule(40, 0, 10000, S, "Homeless each level of an almshouse shelters each epoch")
    almshouse_calm: int = rule(2, 0, 100, S, "Unrest each almshouse calms each epoch")
    almshouse_need_pct: int = rule(5, 0, 100, S, "Share of its people homeless past which a town wants an almshouse (%)")
