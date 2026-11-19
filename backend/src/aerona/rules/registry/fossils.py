from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

E = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class FossilRules:
    richness: int = rule(30, 1, 100, E, "Richness of a fossil bed when it is laid down")
    megafauna_richness: int = rule(60, 1, 100, E, "Richness of a fossil bed of megafauna, a beast or a previous creation")
    old_world_epochs: int = rule(20, 0, 10000, E, "Age in epochs from which a world keeps the remains of peoples that died out on it")
    find_pct: int = rule(2, 0, 100, E, "Chance each epoch an unfound fossil bed is found where nothing disturbs it (%)")
    mine_pct: int = rule(10, 0, 100, E, "Chance a mine or quarry in its land adds each epoch to finding a fossil bed (%)")
    erosion_pct: int = rule(25, 0, 100, E, "Chance a quake or flood in its land that epoch adds to finding a fossil bed (%)")
    reading_from: int = rule(10, -100, 100, E, "Value of superstition, piety or knowledge from which a people reads a find in its way")
    legend_credence: int = rule(10, 0, 100, E, "Credence the legends of a people gain when it reads its find as the remains of beings of its legends")
    relic_followers_pct: int = rule(5, 0, 100, E, "Share of followers the cults of its land gain when a find is read as sacred relics (%)")
    deep_time_strength: int = rule(10, 0, 100, E, "Strength the theories of a people gain when it reads a find as evidence of deep time")
    luxury_per_10: int = rule(2, 0, 100, E, "Units of luxuries every ten points of richness of a found bed yield to its finder")
    son_cost: int = rule(25, 0, 1000, E, "Essence a son spends to lay bare a fossil bed")
    layer_per_epoch: int = rule(2, 0, 100, E, "How much deeper an unfound fossil bed lies with each epoch that passes over it")
    layer_find_cut_pct: int = rule(50, 0, 100, E, "Share of the chance to find it a bed loses at the greatest depth (%)")
    theory_shift: int = rule(10, 0, 100, E, "Strength the theories of a scholar's people gain when the scholar studies a bed")
    fuel_per_10: int = rule(2, 0, 100, E, "Units of fuel every ten points of richness of a found bog or tar bed yield to its finder")
    revival_preservation_min: int = rule(60, 0, 100, E, "Richness a well kept bed needs before a kind it holds can be raised again")
    revival_abundance: int = rule(10, 0, 100, E, "Abundance a kind raised again from its remains has in the land of its bed")
    bog_wetland: int = rule(50, 0, 100, E, "Wetland of a land from which its beds are kept in bog")
    dry_rainfall: int = rule(20, 0, 100, E, "Rainfall of a land below which its beds are kept dry")
