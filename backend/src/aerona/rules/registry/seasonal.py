from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class SeasonalRules:
    disease_wet_pct: int = rule(40, 0, 500, G, "Disease spread and deaths a fully wet sampled year adds in its sickly season (%)")
    disease_heat_pct: int = rule(30, 0, 500, G, "Disease spread and deaths a fully hot sampled year adds in its sickly season (%)")
    disease_season_rain_pct: int = rule(50, 0, 500, G, "Disease a season's rain shift adds per full shift (%)")
    disease_season_floor_pct: int = rule(50, 0, 100, G, "Least seasonal factor of a disease in a dry, cold world (%)")
    disease_season_cap_pct: int = rule(250, 100, 1000, G, "Greatest seasonal factor of a disease (%)")
    food_swing_pct: int = rule(60, 0, 500, G, "Food price swing per point of a sampled year's lost growth (%)")
    goods_swing_pct: int = rule(8, 0, 100, G, "Random price swing of other goods in a sampled year (%)")
    swing_floor_pct: int = rule(50, 1, 100, G, "Lowest a sampled year can push a price (% of its pressure price)")
    swing_cap_pct: int = rule(250, 100, 1000, G, "Highest a sampled year can push a price (% of its pressure price)")
    in_season_pct: int = rule(125, 0, 500, G, "Weight of a tradition kept in its own season (%)")
    off_season_pct: int = rule(60, 0, 100, G, "Weight of a tradition kept out of its season (%)")
    drift_chance: int = rule(35, 0, 100, G, "A tradition kept by folk without a calendar drifts off its season in an epoch (%)")
    plenty_relief_pct: int = rule(50, 0, 100, G, "Share of a feast's food a season of full growth gives for free (%)")
    sleep_custom_chance: int = rule(15, 0, 100, G, "A community under long days or nights founds a sleep custom in an epoch (%)")
    long_day_hours: int = rule(30, 1, 100000, G, "Day length (hours) from which folk rest at noon or keep vigil through the night")
    rest_custom_unrest: int = rule(3, 0, 100, G, "Unrest a custom of rest takes from a settlement")
    rest_custom_satisfaction: int = rule(2, 0, 100, G, "Satisfaction a custom of rest brings each class")
    rest_custom_prosperity: int = rule(1, 0, 100, G, "Prosperity the hours of a custom of rest cost")
    vigil_crime: int = rule(4, 0, 100, G, "Crime a night vigil's watchers take from a settlement")
    vigil_piety: int = rule(1, 0, 100, G, "Piety value a night vigil pushes")
