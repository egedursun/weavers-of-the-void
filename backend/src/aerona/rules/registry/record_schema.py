from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class RecordSchemaRules:
    mystery_threshold: int = rule(55, 0, 100, RuleGroup.EXPLORATION, "Place mystery: a place this mysterious draws lost knowledge and pilgrims")
    mystery_divisor: int = rule(12, 1, 1000, RuleGroup.EXPLORATION, "Place mystery: chance per epoch its secret is solved is mystery divided by this (%)")
    mystery_solved_loss: int = rule(12, 0, 100, RuleGroup.EXPLORATION, "Place mystery: mystery lost when its secret is solved")
    mystery_pilgrim_piety: int = rule(
        4, 0, 100, RuleGroup.EXPLORATION, "Place mystery: piety a nearby community gains from pilgrims when no lost knowledge waits there"
    )
    mystery_cap: int = rule(1, 0, 100, RuleGroup.EXPLORATION, "Place mystery: most secrets solved per epoch")
    function_step: int = rule(3, 0, 100, RuleGroup.CIVILIZATION, "Structure function: most the matching stat rises per epoch")
    function_knowledge_cap: int = rule(2, 0, 100, RuleGroup.CIVILIZATION, "Library or observatory: most knowledges deepened per epoch")
    prophecy_grace: int = rule(3, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: certainty starts to wear after this many epochs")
    certainty_wear: int = rule(3, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: certainty an unfulfilled prophecy loses per epoch")
    certainty_threshold: int = rule(
        60, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: a prophecy this certain holds up the piety of the communities it names"
    )
    certainty_piety_pct: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: piety floor of a named community (percent of certainty)")
    certainty_collapse: int = rule(
        15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: falling below this certainty it is mocked and its god loses renown (once)"
    )
    prophecy_fame_loss: int = rule(3, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Prophecy: renown its god loses when the prophecy is mocked")
