import re

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.domain.enums.environment import MovementMode

VERB_BEFORE_MODE = re.compile(r"\b(travell(?:ing|ed)|going|went|moving|moved)\s+\{(\w+)\}")


def test_a_way_of_travel_is_told_as_a_labelled_value_never_after_a_verb() -> None:
    clumsy = [
        key
        for key, spec in INCIDENT_KINDS.items()
        for _, slot in VERB_BEFORE_MODE.findall(spec.template or "")
        if any(fact.key == slot and fact.enum is MovementMode for fact in spec.facts)
    ]
    assert clumsy == []
