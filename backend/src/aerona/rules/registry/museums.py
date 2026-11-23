from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class MuseumRules(Spanned):
    royal_from: int = rule(3, 1, 100, S, "Prized items a ruler must own before the realm keeps a royal collection")
    specimens_per_epoch: int = rule(1, 0, 100, S, "Living kinds of its land a museum or cabinet takes in as specimens each year")
    prestige_per_piece: int = rule(4, 0, 100, S, "Prestige each piece adds to a collection")
    trophy_prestige: int = rule(5, 0, 50, S, "Martial prestige each trophy of war adds to the hall that keeps it")
    trophy_grievance: int = rule(10, 0, 100, S, "Grievance a people bears against those who carry its banners, arms and regalia off to their hall")
    regalia_shame: int = rule(10, 0, 100, S, "Legitimacy a realm loses when its regalia are carried off")
    manuscript_prestige: int = rule(6, 0, 100, S, "Prestige each manuscript adds to a collection, drawing scholars to its town")
    research_pct: int = rule(2, 0, 100, S, "Research a community gains in a field for each piece of its collections that bears on it (%)")
    research_cap: int = rule(50, 0, 100000, S, "Most pieces that count toward the research of one field")
    loot_pct: int = rule(100, 0, 100, S, "Share of the pieces of its collections a sacked town loses to the sacker (%)")
    son_cost: int = rule(40, 0, 1000, S, "Essence a son spends to found a collection in a town")
