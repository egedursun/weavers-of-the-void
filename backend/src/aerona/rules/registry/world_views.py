from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.COSMOS


@dataclass(frozen=True)
class WorldViewRules:
    star_light_pct: int = rule(100, 0, 200, C, "Share of a harvest that grows under the light of a star (%)")
    lava_light_pct: int = rule(50, 0, 200, C, "Share of a harvest that grows under the glow of lava (%)")
    magic_light_pct: int = rule(60, 0, 200, C, "Share of a harvest that grows under light made by magic (%)")
    inner_sun_light_pct: int = rule(100, 0, 200, C, "Share of a harvest that grows under the sun inside a hollow world (%)")
    divine_light_pct: int = rule(100, 0, 200, C, "Share of a harvest that grows under the light of a god (%)")
    ship_light_pct: int = rule(80, 0, 200, C, "Share of a harvest that grows under the light cycles of a ship (%)")
    fading_light_pct: int = rule(40, 0, 200, C, "Share of a harvest that grows under the fading light of a dead god (%)")
    dark_light_pct: int = rule(0, 0, 200, C, "Share of a harvest that grows where there is no light at all (%)")
    soilless_harvest_pct: int = rule(60, 0, 200, C, "Share of a harvest a world without soil still yields from domes, floating growth or the sea (%)")
    need_per_100: int = rule(2, 0, 100, C, "Units of what a world binds its towns to that every hundred townsfolk need each epoch")
    water_lift_share: int = rule(10, 0, 100, C, "Townsfolk in hundreds whose water need each unit of lifted water meets")
    rain_water_from: int = rule(60, 0, 100, C, "Rainfall of a land from which its towns need no other water")
    belief_from: int = rule(50, 0, 100, C, "Piety of a town from which belief sustains it where a world feeds on belief")
    shortfall_unrest: int = rule(10, 0, 100, C, "Unrest a town gains in an epoch when what its world requires runs out")
    shortfall_prosperity: int = rule(5, 0, 100, C, "Prosperity a town loses in an epoch when what its world requires runs out")
    float_upkeep: int = rule(
        20, 0, 10000, C, "Coin a floating or sealed town pays each epoch for every thousand of its people to stay aloft or sealed (at least this much)"
    )
    upkeep_unpaid_prosperity: int = rule(4, 0, 100, C, "Prosperity a floating or sealed town loses in an epoch it cannot pay its upkeep")
    son_step: int = rule(20, 1, 100, C, "Most a son can move one share of a world's nature in one act")
    son_cost: int = rule(15, 0, 1000, C, "Essence a son spends to move one share of a world's nature")
    terrain_attrition_pct: int = rule(
        5, 0, 100, C, "Share of a land army lost each epoch it marches on a world whose wars are fought at sea, in the sky or by boarding (%)"
    )
