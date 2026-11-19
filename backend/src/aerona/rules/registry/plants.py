from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule, span

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class PlantRules:
    years_to_first_harvest_tree: int = span(5, 0, 50, G, "Years a tree grows before its first harvest")
    storm_damage_tree_pct: int = rule(20, 0, 100, G, "Share of a land's tree and vine crops a storm over it lays down (%)")
    fire_damage_grass_pct: int = rule(40, 0, 100, G, "Share of a land's grass, herb and shrub crops a fire over it burns (%)")
    spread_by_wind_pct: int = rule(10, 0, 100, G, "Chance each epoch that a plant sown by the wind takes root in a neighbouring land (%)")
    spread_by_animal_pct: int = rule(5, 0, 100, G, "Chance each epoch that a plant carried by beasts takes root in a neighbouring land (%)")
    spread_abundance: int = rule(10, 0, 100, G, "Abundance a plant has where it first takes root")
    invasion_kinds: int = rule(6, 1, 100, G, "Kinds of life already in a land at which a newcomer counts as an invader")
    invasion_loss: int = rule(5, 0, 100, G, "Abundance the plants of a land lose to an invader")
    domesticated_share: int = rule(40, 0, 100, G, "Share of a land's fields at which a plant counts as tamed")
