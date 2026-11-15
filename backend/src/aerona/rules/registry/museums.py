from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class MuseumRules:
    royal_from: int = rule(3, 1, 100, S, "Prized items a ruler must own before the realm keeps a royal collection")
    specimens_per_epoch: int = rule(2, 0, 50, S, "Living kinds of its land a museum or cabinet takes in as specimens each epoch")
    prestige_per_piece: int = rule(4, 0, 100, S, "Prestige each piece adds to a collection")
    research_pct: int = rule(2, 0, 100, S, "Research a community gains in a field for each piece of its collections that bears on it (%)")
    research_cap: int = rule(20, 0, 1000, S, "Most pieces that count toward the research of one field")
    loot_pct: int = rule(100, 0, 100, S, "Share of the pieces of its collections a sacked town loses to the sacker (%)")
    son_cost: int = rule(40, 0, 1000, S, "Essence a son spends to found a collection in a town")
