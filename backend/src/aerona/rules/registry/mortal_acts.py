from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MIND
M = RuleGroup.MORTALS
P = RuleGroup.POLITY


@dataclass(frozen=True)
class LoyaltyRules:
    alignment_pct: int = rule(60, 0, 200, G, "How much shared values bind a mortal to their liege, people and god (%)")
    opinion_pct: int = rule(40, 0, 200, G, "How much a mortal's regard for their liege moves their loyalty (%)")
    fear_pct: int = rule(20, 0, 200, G, "How much fear of a liege holds a mortal to them (%)")
    belonging_pct: int = rule(30, 0, 200, G, "How much belonging ties a mortal to their community (%)")
    faith_pct: int = rule(40, 0, 200, G, "How much a fulfilled faith ties a mortal to their god (%)")
    drift_pct: int = rule(30, 0, 100, G, "How fast loyalty moves toward what a mortal now feels (%)")
    conversion_below: int = rule(25, 0, 100, G, "Loyalty to their god below which a mortal may turn to another")
    conversion_chance: int = rule(15, 0, 100, G, "Chance each epoch a mortal unmoored from their god converts to their people's (%)")
    faithless_need_below: int = rule(30, 0, 100, G, "Faith need below which a mortal seeks a new god")


@dataclass(frozen=True)
class ActsRules:
    gratitude_threshold: int = rule(25, 0, 100, G, "Strength of a debt of gratitude that moves a mortal to act")
    gratitude_chance: int = rule(20, 0, 100, G, "Chance each epoch a grateful mortal repays their benefactor (%)")
    gift_wealth: int = rule(8, 0, 100, G, "Wealth a grateful mortal gives away")
    gift_magnitude: int = rule(20, 0, 100, G, "How warmly a benefactor remembers a gift of thanks")
    plot_grievance: int = rule(30, 0, 100, G, "Grievance toward their liege at which a scheming mortal plots")
    plot_loyalty_below: int = rule(35, 0, 100, G, "Loyalty to the liege below which a mortal will plot")
    plot_chance: int = rule(15, 0, 100, G, "Chance each epoch a grieved, scheming mortal plots against their liege (%)")
    plot_discovery_pct: int = rule(100, 0, 400, G, "How much the liege's perception uncovers plots (%)")
    plot_success_magnitude: int = rule(30, 0, 100, G, "How bitterly a betrayed liege remembers a plot that succeeded")
    plot_renown: int = rule(6, 0, 100, G, "Renown a successful plotter wins")
    plot_wealth: int = rule(12, 0, 100, G, "Wealth a successful plotter seizes from their liege")


@dataclass(frozen=True)
class EthnicRules:
    tension_below: int = rule(-20, -100, 100, P, "Regard between two peoples of one realm below which strife breaks out")
    strife_chance: int = rule(20, 0, 100, P, "Chance each epoch that hostile peoples of one realm clash (%)")
    strife_unrest: int = rule(10, 0, 100, P, "Unrest a clash between peoples adds to the realm's towns")
    strife_population_pct: int = rule(2, 0, 100, P, "Share of the weaker people lost in a clash (%)")
    strife_stability: int = rule(8, 0, 100, P, "Stability a realm loses to strife between its peoples")
    strife_magnitude: int = rule(15, 0, 100, P, "How bitterly the peoples remember a clash")
    harmony_above: int = rule(40, -100, 100, P, "Regard between two peoples of one realm above which they draw closer")
    harmony_relation: int = rule(3, 0, 100, P, "Regard two harmonious peoples of one realm gain each epoch")
