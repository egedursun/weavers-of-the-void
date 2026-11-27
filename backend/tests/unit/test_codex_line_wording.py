import re

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import fact_word, spoken
from aerona.domain.enums.ages import ArcOutcome, ArcTemplate
from aerona.domain.enums.collective import FormativeKind
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.interpretation import InterpretationFault
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.recording.render import render_incident

HOUSEHOLD_TWICE = re.compile(r"\{household\}, the household of")


def test_a_household_line_names_the_household_once() -> None:
    assert [key for key, spec in INCIDENT_KINDS.items() if HOUSEHOLD_TWICE.search(spec.template or "")] == []


def test_a_name_that_starts_with_an_article_reads_lowercase_inside_a_sentence() -> None:
    spec = INCIDENT_KINDS["polity.law_enacted"]
    text = render_incident(spec, {IncidentRole.AUTHORITY: ["Ilsaren"], IncidentRole.PRODUCT: ["The levy law of Ilsaren"]}, {"rule": "autocratic"})
    assert "passed the levy law of Ilsaren" in text


def test_ends_guards_and_formative_times_read_as_phrases() -> None:
    ended = render_incident(INCIDENT_KINDS["arcs.ended"], {IncidentRole.SUBJECT: ["Osmem"]}, {"template": ArcTemplate.REVENGE, "outcome": ArcOutcome.FAILED})
    grave = render_incident(INCIDENT_KINDS["dead.goods_placed"], {IncidentRole.SUBJECT: ["Alre"]}, {"items": 0, "value": 1, "guard": GraveGuard.NONE})
    shaped = render_incident(INCIDENT_KINDS["generations.came_of_age"], {IncidentRole.PLACE: ["Solhar"]}, {"formative": [FormativeKind.LONG_SEASON]})
    assert ended.endswith("ended in failure.")
    assert grave.endswith("the grave was left unguarded.")
    assert "shaped by a long season" in shaped


def test_members_of_two_enums_that_share_a_value_each_speak_their_own_word() -> None:
    first, second = InterpretationFault.NONE, GraveGuard.NONE
    assert (spoken(first), spoken(second)) == (fact_word("InterpretationFault", "none"), fact_word("GraveGuard", "none"))
    assert spoken(second) != spoken(first)
