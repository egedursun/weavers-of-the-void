from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import an
from aerona.domain.enums.collective import CommemorationFeeling
from aerona.domain.enums.genetics import HouseholdDecision
from aerona.domain.enums.governance import HeadSelection
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.relations import AppealKind, PersuasionAim
from aerona.engine.disease.emergence import plain
from aerona.engine.recording.render import render_incident
from aerona.services.ledger import action_label


def told(key: str, names: dict[IncidentRole, list[str]], facts: dict[str, object]) -> str:
    return render_incident(INCIDENT_KINDS[key], names, facts)


def test_articles_follow_the_sound_of_the_word() -> None:
    assert [an(word) for word in ("union", "use", "hour", "heir", "echo", "idea")] == ["a union", "a use", "an hour", "an heir", "an echo", "an idea"]


def test_a_strain_of_a_strain_is_named_from_the_first_sickness() -> None:
    assert plain("The spirit-borne sickness, strain 2, strain 2") == "spirit-borne sickness"


def test_upkeep_acts_read_as_acts() -> None:
    assert action_label("maintenance:data_repairs") == "ran the upkeep of data repairs"


def test_a_titled_happening_takes_its_article_mid_sentence() -> None:
    line = told(
        "history.anniversary",
        {IncidentRole.SUBJECT: ["Ilsaren"]},
        {"feeling": next(iter(CommemorationFeeling)), "happening": "War of Denvosa", "years": 50, "shift": 1},
    )
    assert "of the War of Denvosa" in line


def test_household_lines_name_the_household_once() -> None:
    line = told("households.take_lodger", {IncidentRole.ACTOR: ["Orur"]}, {"household": "Household of Orur", "decision": HouseholdDecision.TAKE_LODGER})
    assert line == "Household of Orur chose to take in a lodger."


def test_laws_heads_and_appeals_read_as_plain_english() -> None:
    law = told("polity.law_proposed", {IncidentRole.ACTOR: ["Abem"], IncidentRole.AUTHORITY: ["Zemoth"]}, {"law": LawKind.BURIAL_LAW})
    head = told(
        "org.head_chosen",
        {IncidentRole.ACTOR: ["Cenjuc"], IncidentRole.SUBJECT: ["Kirdasa"]},
        {"selection": HeadSelection.ELECTED_BY_MEMBERS, "why": "the head was gone"},
    )
    talk = told(
        "social.persuaded",
        {IncidentRole.ACTOR: ["Cenjuc"], IncidentRole.TARGET: ["Upjuc"]},
        {"appeal": AppealKind.EVIDENCE, "aim": PersuasionAim.CONFESSION, "score": 52},
    )
    assert "law law" not in law and "burial law" in law
    assert "by election by its members" in head
    assert "by appeal to evidence, toward a confession" in talk
