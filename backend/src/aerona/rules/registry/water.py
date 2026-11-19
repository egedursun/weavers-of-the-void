from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class WaterAndIceRules:
    silting_per_epoch: int = rule(2, 0, 50, G, "Harbour silting a full load of sediment lays at its sink each epoch")
    dredge_cost: int = rule(10, 0, 500, G, "Coin that clears one point of a harbour's silting")
    coast_wear_per_epoch: int = rule(1, 0, 50, G, "How far a coast with no sediment wears away each epoch")
    delta_growth_per_epoch: int = rule(1, 0, 50, G, "How far a full load of sediment builds its coast out each epoch")
    thaw_collapse_pct: int = rule(5, 0, 100, G, "Chance that a thawing of frozen ground brings down the works of a town on it (%)")
    snow_water_share_pct: int = rule(30, 0, 100, G, "Share of the water downstream that the snowpack of a land gives in its melt season (%)")
    ice_route_block_months: int = rule(3, 0, 12, G, "Months of ice a year at which ice closes the sea and river roads of a land")
    local_heat_per_density: int = rule(1, 0, 10, G, "Warmth a town adds to its own climate for each thousand who live in it")
    snow_drought_below: int = rule(15, 0, 100, G, "Snowpack below which a land that lives on its snow has a dry summer downstream")
    snow_drought_loss: int = rule(7, 0, 100, G, "Prosperity a town downstream would lose in a snow drought if all its water came from the snow")
    silted_loss: int = rule(5, 0, 50, G, "Prosperity a harbour town loses when its harbour silts up")
    coast_loss: int = rule(3, 0, 50, G, "Prosperity a coastal town loses when the sea takes its fields")
    delta_fertility: int = rule(5, 0, 50, G, "Soil fertility a land gains when its delta grows")
    thaw_loss: int = rule(4, 0, 50, G, "Prosperity a town loses when the thaw brings down its works")
    thaw_step: int = rule(10, 1, 100, G, "Fall of frozen depth in one epoch that counts as a thaw")
    glacier_step: int = rule(10, 1, 100, G, "Change of a glacier's extent in one epoch that counts as an advance or a retreat")
    heat_outbreak: int = rule(1, 0, 20, G, "Severity an outbreak in a hot crowded town gains each epoch")
    heat_threshold: int = rule(10, 0, 50, G, "Warmth a town adds to its own climate at which its heat feeds disease")
    river_load: int = rule(20, 0, 100, G, "Load of sediment a river carries to the land below it")
    great_river_load: int = rule(40, 0, 100, G, "Load of sediment a great river carries to the land below it")
    wind_load: int = rule(10, 0, 100, G, "Load of sand the wind carries from a desert to its neighbours")
    ice_change_max: int = rule(12, 0, 12, G, "Most months of ice a god can add or take away in one deed")
