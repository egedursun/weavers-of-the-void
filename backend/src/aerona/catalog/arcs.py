from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ages import ArcTemplate
from aerona.rules.registry import Rules

A = ArcTemplate


@dataclass(frozen=True)
class ArcSpec:
    label: str
    weight: Callable[[Rules], int]
    confronting: bool = False
    ends_in_death: bool = False
    monomyth: bool = False


ARCS: Mapping[ArcTemplate, ArcSpec] = total(
    ArcTemplate,
    {
        A.RISE_AND_FALL: ArcSpec("Rise and fall", lambda rules: rules.arcs.rise_and_fall_weight, ends_in_death=True),
        A.RAGS_TO_RICHES: ArcSpec("Rags to riches", lambda rules: rules.arcs.rags_to_riches_weight),
        A.REVENGE: ArcSpec("Revenge", lambda rules: rules.arcs.revenge_weight, confronting=True),
        A.REDEMPTION: ArcSpec("Redemption", lambda rules: rules.arcs.redemption_weight),
        A.QUEST: ArcSpec("Quest", lambda rules: rules.arcs.quest_weight, monomyth=True),
        A.TRAGEDY: ArcSpec("Tragedy", lambda rules: rules.arcs.tragedy_weight, ends_in_death=True),
        A.FORBIDDEN_LOVE: ArcSpec("Forbidden love", lambda rules: rules.arcs.forbidden_love_weight),
        A.RIVALRY: ArcSpec("Rivalry", lambda rules: rules.arcs.rivalry_weight, confronting=True),
        A.MENTOR_AND_HEIR: ArcSpec("Mentor and heir", lambda rules: rules.arcs.mentor_and_heir_weight),
        A.EXILE_AND_RETURN: ArcSpec("Exile and return", lambda rules: rules.arcs.exile_and_return_weight),
        A.CORRUPTION: ArcSpec("Corruption", lambda rules: rules.arcs.corruption_weight, ends_in_death=True),
        A.COMING_OF_AGE: ArcSpec("Coming of age", lambda rules: rules.arcs.coming_of_age_weight),
        A.FALL_OF_A_HOUSE: ArcSpec("Fall of a house", lambda rules: rules.arcs.fall_of_a_house_weight, ends_in_death=True),
        A.FOUNDING: ArcSpec("Founding", lambda rules: rules.arcs.founding_weight),
        A.APOTHEOSIS: ArcSpec("Apotheosis", lambda rules: rules.arcs.apotheosis_weight),
        A.OVERCOMING: ArcSpec("Overcoming", lambda rules: rules.arcs.overcoming_weight, confronting=True),
        A.RECONCILIATION: ArcSpec("Reconciliation", lambda rules: rules.arcs.reconciliation_weight),
        A.SACRIFICE: ArcSpec("Sacrifice", lambda rules: rules.arcs.sacrifice_weight, ends_in_death=True),
        A.DISCOVERY: ArcSpec("Discovery", lambda rules: rules.arcs.discovery_weight),
    },
)
CONFRONTING = frozenset(template for template, spec in ARCS.items() if spec.confronting)
ENDS_IN_DEATH = frozenset(template for template, spec in ARCS.items() if spec.ends_in_death)
