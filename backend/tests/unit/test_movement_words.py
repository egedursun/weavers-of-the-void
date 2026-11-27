import re

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import fact_word
from aerona.domain.enums.environment import MovementMode

GOING = re.compile(r"\b(?:going|went)\s+\{(\w+)\}")


def test_a_way_of_moving_told_after_going_reads_as_a_manner_not_a_pastime() -> None:
    leisure = [
        f"{key}: {fact_word(MovementMode.__name__, mode.value)}"
        for key, spec in INCIDENT_KINDS.items()
        for slot in GOING.findall(spec.template or "")
        for fact in spec.facts
        if fact.key == slot and fact.enum is MovementMode
        for mode in MovementMode
        if fact_word(MovementMode.__name__, mode.value).endswith("ing") and " " not in fact_word(MovementMode.__name__, mode.value)
    ]
    assert leisure == []
