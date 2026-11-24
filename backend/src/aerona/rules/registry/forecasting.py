from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class ForecastingRules:
    accuracy_sight: int = rule(20, 0, 100, G, "Accuracy of a forecast read by sight of the sky")
    accuracy_lore: int = rule(35, 0, 100, G, "Accuracy of a forecast read from lore")
    accuracy_almanac: int = rule(45, 0, 100, G, "Accuracy of a forecast read from an almanac")
    accuracy_instrument: int = rule(60, 0, 100, G, "Accuracy of a forecast read from instruments")
    accuracy_network_of_observers: int = rule(70, 0, 100, G, "Accuracy of a forecast read by a network of observers")
    accuracy_model: int = rule(85, 0, 100, G, "Accuracy of a forecast read from a model")
    accuracy_network: int = rule(80, 0, 100, G, "Accuracy of a forecast read over a network of machines")
    accuracy_power: int = rule(50, 0, 100, G, "Accuracy of a forecast read by a power")
    accuracy_divination: int = rule(30, 0, 100, G, "Accuracy of a forecast read by divination")
    accuracy_animal_signs: int = rule(45, 0, 100, G, "Accuracy of a forecast read from the signs of animals with keen senses")
    accuracy_dream: int = rule(25, 0, 100, G, "Accuracy of a forecast read from dreams")
    snow_work_snowpack: int = rule(30, 0, 100, G, "Snowpack below which a town whose rivers run from glaciers works the weather for snow")
    wind_work_harbour: int = rule(20, 0, 100000, G, "Harbour capacity from which a town works the weather for wind to sail by")
    weather_work_strength: int = rule(20, 0, 100, G, "Strength of a weather work a mortal raises at the usual effort")
    weather_work_cost: int = rule(20, 0, 500, G, "Coin a weather work costs at the usual effort")
    weather_work_shift: int = rule(40, 0, 100, G, "Shift of a land's rainfall from its usual at which its towns try to work the weather back")
    side_effect_share_pct: int = rule(50, 0, 100, G, "Share of a weather work's strength that falls on the land downwind as its opposite (%)")
    kept_accuracy: int = rule(50, 0, 100, G, "Accuracy at which a people's forecast foresees a failed or turned season")
    kept_refund: int = rule(2, 0, 50, G, "Prosperity a town keeps in a hard season because its people foresaw it")
    ignore_piety: int = rule(70, 0, 100, G, "Piety above which a people does not believe a forecast read by instruments, observers or models")
    navigation_share_pct: int = rule(20, 0, 100, G, "Share of a people's best sky or weather accuracy its pilots gain (%)")
    sky_mark_accuracy: int = rule(5, 0, 100, G, "Accuracy a people gains in reading the sky for each body of the heavens it watches and can see")
    sky_mark_cap: int = rule(20, 0, 100, G, "Most accuracy a people gains from the bodies of the heavens it watches")
    grievance: int = rule(5, 0, 100, G, "Relation a community downwind loses toward the worker of a weather work that harms it")
    ban_relation: int = rule(-50, -100, 100, G, "Relation below which a harmed community makes the worker stop a weather work")
