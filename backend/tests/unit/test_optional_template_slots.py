import re
from string import Formatter

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec
from aerona.core.grammar import OPTIONAL_MARK, fill
from aerona.domain.enums.records import FactValue
from aerona.engine.recording.render import indexed, render_incident

FIELDS = Formatter()
LEFT_BEHIND = re.compile(
    r"\b(of|to|toward|towards|for|against|from|with|by|at|in|into|onto|on|upon|between|among|as|under|through|via|about|after|before"
    r"|within|without|beside|near|across|behind|beyond|than|amid|unto|its|their|the|a|an|this|that|whose)\{[^}:]+:\?"
)
CUT_CLAUSE = re.compile(r"[,;:]\{[^}:]+:\?[^}]*\}\s*[a-z]|\{[^}:]+:\?[,;][^}]*[^,;]\}\s*[a-z]")
BROKEN = re.compile(r"\s[,.;:!?]|,\s*[,.;:!?]|\(\s*\)|^[,.;:]")


def leading_optional(spec: IncidentKindSpec) -> str | None:
    for literal, name, _, _ in FIELDS.parse(spec.template):
        if literal and literal.strip():
            return None
        if name:
            base = name.split("[")[0].split(".")[0]
            return base if base in optional_names(spec) else None
    return None


def optional_names(spec: IncidentKindSpec) -> set[str]:
    return {role.role.value for role in spec.roles if not role.required} | {fact.key for fact in spec.facts if not fact.required}


def bare_slots(spec: IncidentKindSpec) -> list[str]:
    found: list[str] = []
    optional = optional_names(spec)
    first = True
    for literal, name, format_spec, _ in FIELDS.parse(spec.template):
        if name:
            base = name.split("[")[0].split(".")[0]
            spaced = (first and not literal) or (bool(literal) and literal[-1].isspace())
            if base in optional and spaced and not (format_spec or "").startswith(OPTIONAL_MARK):
                found.append(name)
            first = False
        elif literal:
            first = False
    return found


def sample(fact: FactSpec) -> object:
    if fact.value is FactValue.NUMBER:
        return 2
    if fact.value is FactValue.ENUM:
        return next(iter(fact.enum)) if fact.enum is not None else "value"
    return f"the {fact.key.replace('_', ' ')}"


def told_without(spec: IncidentKindSpec, left_out: str) -> str:
    needed = indexed(spec.template)
    names = {
        role.role: [f"the {role.role.value} {count + 1}" for count in range(max(1, needed.get(role.role.value, 1)))]
        for role in spec.roles
        if role.role.value != left_out
    }
    facts = {fact.key: [sample(fact)] if fact.many else sample(fact) for fact in spec.facts if fact.key != left_out}
    return render_incident(spec, names, facts)


def told_kinds() -> list[IncidentKindSpec]:
    return [spec for spec in INCIDENT_KINDS.values() if spec.told and not spec.draft]


def test_an_optional_segment_is_told_only_when_its_value_is_there() -> None:
    assert fill("Ama acted{target:? toward #}.", target="Bel") == "Ama acted toward Bel."
    assert fill("Ama acted{target:? toward #}.", target="") == "Ama acted."


def test_every_optional_slot_spaced_into_a_template_is_an_optional_segment() -> None:
    assert [f"{spec.key}: {name}" for spec in told_kinds() for name in bare_slots(spec)] == []


def test_no_optional_segment_leaves_its_preposition_or_article_behind() -> None:
    assert [f"{spec.key}: {spec.template}" for spec in told_kinds() if LEFT_BEHIND.search(spec.template) or CUT_CLAUSE.search(spec.template)] == []


def test_every_kind_reads_cleanly_with_any_optional_role_or_fact_left_out() -> None:
    broken = [
        f"{spec.key} without {name}: {text}"
        for spec in told_kinds()
        for name in sorted(optional_names(spec))
        if BROKEN.search(text := told_without(spec, name))
    ]
    assert broken == []


def test_no_kind_opens_with_a_value_that_may_be_missing() -> None:
    assert [f"{spec.key}: {spec.template}" for spec in told_kinds() if not spec.legacy and leading_optional(spec) is not None] == []
