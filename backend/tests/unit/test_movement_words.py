import re

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.domain.enums.environment import MovementMode

GOING = re.compile(r"\b(?:going|went|goes|go)\s+\{(\w+)\}")


def test_a_way_of_moving_is_told_after_a_verb_of_travel_that_takes_a_manner() -> None:
    clumsy = [
        f"{key}: {slot}"
        for key, spec in INCIDENT_KINDS.items()
        for slot in GOING.findall(spec.template or "")
        for fact in spec.facts
        if fact.key == slot and fact.enum is MovementMode
    ]
    assert clumsy == []
