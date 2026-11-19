from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MIND


@dataclass(frozen=True)
class FolkKnowledgeRules:
    accuracy_success_pct: int = rule(50, 0, 100, M, "Share by which the accuracy of a people's knowledge in a domain moves success in the work it serves")
    loss_on_holder_death_pct: int = rule(
        10, 0, 100, M, "Chance each epoch that knowledge held by elders or specialists loses depth when one of its people dies"
    )
    contact_gain: int = rule(5, 0, 50, M, "Accuracy a people gains in a domain each epoch from a neighbouring people that knows it better")
    failure_correction: int = rule(10, 0, 100, M, "Accuracy a people gains when a misclassification fails it and the class is put right")
    harm_chance_pct: int = rule(
        20, 0, 100, M, "Chance each epoch that a harmful misclassification hurts someone, scaled by how inaccurate the people's knowledge is"
    )
    harm_hp: int = rule(10, 0, 100, M, "Health a mortal loses when something harmful is taken for food, medicine or harmless")
    curse_blame_unrest: int = rule(5, 0, 100, M, "Unrest a town gains when an illness taken for a curse is blamed on someone")
    schooling_gain: int = rule(2, 0, 50, M, "Accuracy a people gains in every domain each epoch while one of its towns keeps a school")
    class_span: int = rule(10, 1, 100, M, "Depth of knowledge needed for each class a people names in a domain")
    theory_pull_pct: int = rule(
        20, 0, 100, M, "Share of the gap to a formal theory's correctness that a people's knowledge moves each epoch where the people holds that theory"
    )
    numerology_piety: int = rule(3, 0, 100, M, "Piety a town gains in an epoch whose number its people reads as sacred")
    numerology_unrest: int = rule(
        3, 0, 100, M, "Unrest a town gains in an epoch whose number its people reads as unlucky or forbidden, and loses in one read as lucky"
    )
    numerology_name_renown: int = rule(5, 0, 100, M, "Renown a child born in an epoch its people reads as lucky starts with")
