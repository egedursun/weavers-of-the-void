from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class KindsRules:
    spread_pct: int = rule(12, 0, 100, G, "Chance each epoch a people that holds a kind passes it to a neighbour or a trading partner, at full strength (%)")
    prestige_spread_pct: int = rule(30, 0, 200, G, "Share of a kind's prestige added to its chance to spread (%)")
    adoption_strength: int = rule(20, 1, 100, G, "Strength with which a people first holds a kind it has taken from another")
    novelty_epochs: int = rule(4, 1, 100, G, "Epochs a newly taken kind keeps gaining strength before its novelty wears off")
    novelty_gain: int = rule(6, 0, 50, G, "Strength a kind gains each epoch while it is new to its holder")
    novelty_fade: int = rule(3, 0, 50, G, "Strength a kind loses each epoch once its novelty has worn off")
    founding_strength: int = rule(60, 1, 100, G, "Strength with which a people holds a kind it has just made")
    prestige_hold_pct: int = rule(5, 0, 100, G, "Share of a kind's prestige that holds its strength up each epoch (%)")
    retire_epochs: int = rule(6, 1, 1000, G, "Epochs after which a kind that no one holds any more is retired")
    blessing_strength: int = rule(25, 0, 100, G, "Strength a god's blessing adds to a kind among a people")
    founded_per_people: int = rule(24, 0, 200, G, "Kinds of things a people can make at its awakening or in one deepening")
    scarcity_index: int = rule(170, 100, 1000, G, "Price index of a good, against its base price, at which the kinds tied to it are called dear")
    substitution_pct: int = rule(20, 0, 100, G, "Chance each epoch a people holding a kind tied to a dear good makes a substitute from a cheaper good (%)")
    substitute_value_pct: int = rule(25, 0, 100, G, "Share by which a substitute's value and prestige fall below the kind it replaces (%)")
    substitution_fade: int = rule(15, 0, 100, G, "Strength the replaced kind loses among the people that made a substitute")
    fusion_strength: int = rule(40, 0, 100, G, "Strength at which two kinds of one category held by one people may fuse into a new one")
    fusion_pct: int = rule(8, 0, 100, G, "Chance each epoch two strongly held kinds of one category from different makers fuse into a new kind (%)")
    prestige_gain: int = rule(4, 0, 50, G, "Prestige a kind gains each epoch as its holders grow toward the saturation count")
    prestige_saturation: int = rule(6, 1, 1000, G, "Holders at which a kind is everywhere and its prestige begins to wear thin")
    prestige_fade: int = rule(3, 0, 50, G, "Prestige a kind loses each epoch once it is held everywhere")
    context_lines: int = rule(6, 0, 40, G, "Kinds of things a mortal or a son is told about in one turn")
    tenet_pull_pct: int = rule(10, 0, 100, G, "Share of a held tenet's pull that moves its holders' values each epoch, at full strength (%)")
    aim_pull_pct: int = rule(50, 0, 200, G, "Share of a held aim's pull added to a mortal's wish for the goal of its category (%)")
