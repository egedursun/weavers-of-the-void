from aerona.catalog.god_lines import Line
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec
from aerona.core.grammar import an, fill, several, spoken
from aerona.domain.enums.records import FactValue
from aerona.engine.recording.render import render_incident
from aerona.prompts.environment import environment


def test_an_picks_the_article_by_sound() -> None:
    assert [an(word) for word in ("empire", "oak", "umbra", "kingdom")] == ["an empire", "an oak", "an umbra", "a kingdom"]
    assert [an(number) for number in (8, 9, 11, 18, 110, 18000)] == ["an 8", "a 9", "an 11", "an 18", "a 110", "an 18000"]
    assert an("island", capital=True) == "An island"


def test_templates_fill_articles_by_their_words() -> None:
    assert fill("{x:an} and {y:An}", x="ash", y="bell") == "an ash and A bell"
    assert Line("probe", "{me} issued {kind:an} mandate.").render(me="Ilsa", kind="export ban") == "Ilsa issued an export ban mandate."
    assert environment().from_string("{{ kind | an }}; {{ kind | an(capital=True) }}").render(kind="empire") == "an empire; An empire"


def test_a_count_of_one_reads_in_the_singular() -> None:
    assert several(1, "piece of evidence", "pieces of evidence") == "1 piece of evidence"
    assert several(0, "age-set", "age-sets") == "0 age-sets"
    assert several(3, "youth", "youths") == "3 youths"
    assert several(None, "moon", "moons") == "an unknown number of moons"
    assert fill("{count:person|people} set out", count=1) == "1 person set out"
    assert fill("{count:person|people} set out", count=4) == "4 people set out"


def test_a_plural_field_reads_a_count_stored_as_a_float() -> None:
    assert fill("{actor} freed {count:captive|captives}.", actor="Fadrine", count=3.0) == "Fadrine freed 3 captives."
    assert fill("{count:captive|captives}", count=1.0) == "1 captive"
    assert fill("{count:captive|captives}", count=2.5) == "2.5 captives"


def told_fact(fact: FactSpec, number: float) -> object:
    if fact.value is FactValue.NUMBER:
        value: object = number
    elif fact.value is FactValue.ENUM and fact.enum is not None:
        value = spoken(next(iter(fact.enum)))
    else:
        value = fact.key
    return [value, value] if fact.many else value


def test_every_incident_template_tells_its_line_whatever_number_type_its_facts_come_back_as() -> None:
    for spec in INCIDENT_KINDS.values():
        if not spec.template:
            continue
        names = {role.role: ["Fadrine", "Ilsaveth"] for role in spec.roles}
        for number in (1.0, 3.0, 7, 2.5):
            facts = {fact.key: told_fact(fact, number) for fact in spec.facts}
            assert render_incident(spec, names, facts), spec.key
