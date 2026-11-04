from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class IncitementRules:
    fame_per_battle: int = rule(2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Fame a god gains for each battle fought in a war they incited")
    fame_cap: int = rule(30, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Most fame one incited war can bring its instigator")
    patron_victory_existence: int = rule(
        3, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Existence a god gains when the side worshipping them wins the war they incited"
    )
    patron_defeat_existence: int = rule(
        4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Existence a god loses when the side worshipping them loses the war they incited"
    )
    loser_grievance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Grievance the losers of an incited war keep against the god who set it off")
