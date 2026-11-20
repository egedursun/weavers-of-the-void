import re

from aerona.catalog.god_lines import Line
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec
from aerona.core.grammar import an, fill, plural, several, spoken
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


def test_no_count_form_puts_its_number_before_a_word_that_is_already_a_quantity() -> None:
    quantity = re.compile(r"\{\w+:(one|many|a|an|some|no|several)\b[^}|]*\|[^}|]*\}")
    assert [key for key, spec in INCIDENT_KINDS.items() if quantity.search(spec.template or "")] == []


def test_a_span_of_none_reads_as_less_than_one() -> None:
    assert fill("after {n:epoch|epochs}", n=0) == "after less than one epoch"
    assert fill("for {n:round|rounds}", n=0) == "for less than one round"
    assert fill("{n:coin|coins}", n=0) == "no coins"


def test_a_count_of_none_reads_as_no_thing_and_never_as_a_bare_zero() -> None:
    assert fill("{displaced:hand|hands} lost their work.", displaced=0) == "no hands lost their work."
    assert fill("{lost:person was|people were} lost.", lost=0.0) == "no people were lost."
    assert fill("{displaced:hand|hands} lost their work.", displaced=2) == "2 hands lost their work."


def test_a_noun_takes_its_plural_by_its_ending() -> None:
    words = ("barrel", "chest", "amphora", "chain pump", "water screw", "box", "city", "day", "wife", "charts", "species", "guide of souls")
    plurals = ["barrels", "chests", "amphoras", "chain pumps", "water screws", "boxes", "cities", "days", "wives", "charts", "species", "guides of souls"]
    assert [plural(word) for word in words] == plurals
    assert [several(count, "crate", plural("crate")) for count in (1, 29)] == ["1 crate", "29 crates"]


def test_a_count_can_read_differently_at_none_one_and_many() -> None:
    spec = "{n:within the epoch it was begun|after # epoch|after # epochs}"
    assert [fill(spec, n=n) for n in (0, 1, 3)] == ["within the epoch it was begun", "after 1 epoch", "after 3 epochs"]


def test_a_told_clause_that_ends_its_own_sentence_is_not_stopped_twice() -> None:
    spec = INCIDENT_KINDS["structures.finished"]
    trade = next(kind for kind in INCIDENT_KINDS.values() if kind.template.startswith("{giver} began to trade with {receiver}: {goods}."))
    names = {role.role: ["Hesarun"] for role in trade.roles}
    assert render_incident(trade, names, {"goods": "fish for algae."}).endswith("fish for algae.")
    assert render_incident(trade, names, {"goods": "they waited..."}).endswith("they waited...")
    assert render_incident(trade, names, {"goods": "who knows?"}).endswith("who knows?")
    assert "after 0" not in render_incident(
        spec,
        {role.role: ["Elumeth"] for role in spec.roles},
        {fact.key: 0 for fact in spec.facts if fact.value is FactValue.NUMBER} | {"structure": "a power plant"},
    )


def test_a_line_always_closes_and_never_doubles_an_article_before_a_name() -> None:
    denied = INCIDENT_KINDS["tools.mortal.denied_all"]
    assert render_incident(denied, {role.role: ["Ost"] for role in denied.roles}, {"reason": "for my people"}).endswith("for my people.")
    spread = INCIDENT_KINDS["culture.language_spread"]
    line = render_incident(spread, {role.role: ["the Ost Folk"] for role in spread.roles}, {})
    assert "the the" not in line.lower()


def test_a_blank_remark_leaves_no_stray_colon_or_brackets() -> None:
    power = INCIDENT_KINDS["tools.son.wield_power"]
    line = render_incident(power, {role.role: ["Ost"] for role in power.roles if role.required}, {"power": "the tide"})
    assert not line.rstrip(".").endswith(":") and line.endswith(".")


def test_no_template_names_a_realm_twice_when_its_name_already_says_realm() -> None:
    doubled = re.compile(r"\b(realm|title|people|town|city) (of )?the \1\b", re.IGNORECASE)
    found = []
    for spec in INCIDENT_KINDS.values():
        if not spec.template:
            continue
        names = {role.role: ["the realm of Ost"] for role in spec.roles}
        facts = {fact.key: told_fact(fact, 3) if fact.value is not FactValue.NAME else "the realm of Ost" for fact in spec.facts}
        if doubled.search(render_incident(spec, names, facts)):
            found.append(spec.key)
    assert found == []


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
