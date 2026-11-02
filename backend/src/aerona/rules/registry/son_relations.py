from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class SonRelationsRules:
    devotion: int = rule(60, -100, 100, RuleGroup.WAR_AND_DIPLOMACY, "Between sons: this and above is devotion")
    friendship: int = rule(25, -100, 100, RuleGroup.WAR_AND_DIPLOMACY, "Between sons: this and above is friendship")
    hostility: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Between sons: minus this and below is hostility")
    hatred: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Between sons: minus this and below is hatred")
