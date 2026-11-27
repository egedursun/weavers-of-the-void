import re

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import fact_word

LEADING = re.compile(r"\b(by|through|with|from)\s+\{(\w+)(?::[^}]*)?\}(?=[.,;:)]|$)")
LINKING = frozenset({"by", "within", "to", "from", "with", "into", "out", "off", "up", "down"})
NOUNS_IN_ED = frozenset({"bloodshed", "creed", "deed", "need", "seed", "speed", "steed", "breed", "reed", "bed"})


def bare_participle(word: str) -> bool:
    words = word.split()
    verbal = words[0].endswith("ed") and words[0] not in NOUNS_IN_ED
    return verbal and (len(words) == 1 or words[1] in LINKING)


def test_a_fact_told_after_by_through_with_or_from_reads_as_a_noun_for_every_value() -> None:
    clumsy: list[str] = []
    for key, spec in INCIDENT_KINDS.items():
        facts = {fact.key: fact for fact in spec.facts}
        for preposition, slot in LEADING.findall(spec.template or ""):
            fact = facts.get(slot)
            if fact is None or fact.enum is None:
                continue
            for value in fact.enum:
                word = fact_word(fact.enum.__name__, value.value)
                if bare_participle(word) or word.startswith(f"{preposition} "):
                    clumsy.append(f"{key}: {preposition} {word}")
    assert clumsy == []
