from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EmptyWorldRules:
    dispatch_wait_epochs: int = rule(
        1,
        0,
        1000,
        RuleGroup.COSMOS_AND_TRAVEL,
        "When an empty but habitable world stays empty this many epochs, a son turns to it on his own (0 = immediately)",
    )
    first_people_essence: int = rule(
        30, 0, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Essence reward for the son who creates the first people, settlement or named mortal of an empty world"
    )
    first_people_renown: int = rule(10, 0, 10000, RuleGroup.COSMOS_AND_TRAVEL, "Renown reward for the son who creates the first people of an empty world")
    first_people_xp: int = rule(20, 0, 10000, RuleGroup.COSMOS_AND_TRAVEL, "XP reward for the son who creates the first people of an empty world")
    native_guarantee_epochs: int = rule(
        3, 0, 1000, RuleGroup.POPULATION_AND_GROWTH, "If a world stays without a people this many epochs, a native people certainly appears (0 = no guarantee)"
    )
    opportunity_regions: int = rule(3, 1, 50, RuleGroup.OPPORTUNITIES, "Habitable regions listed in the new-world opportunity")
