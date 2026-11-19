import importlib
import pkgutil
import re
from collections.abc import Iterator
from enum import StrEnum

import aerona.domain.enums as enum_package
from aerona.catalog.estates import ESTATE_NAMES
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.ownership import OWNER_LABELS
from aerona.catalog.society import SOCIAL_CLASSES
from aerona.catalog.titles import RANK_WORDS
from aerona.core.grammar import AGE_NEUTRAL, spoken
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactValue
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.lifecycle.ruler_roles import BASE_ROLES, CLASS_ROLES
from aerona.engine.phases.births import NOTABLE_ROLES, RULER_TITLES
from aerona.engine.phases.factions import BLUEPRINTS
from aerona.engine.phases.world_balance import FACTION_KINDS, TRADITIONS
from aerona.engine.recording.render import render_incident

ERA_BOUND = re.compile(
    r"\b(scribes?|guilds?|guildhalls?|guildmaster\w*|crown(ed|s|ing)?|coronations?|smiths?|smithing|peasants?|peasantry|"
    r"serfs?|lords?|lordship|kingdoms?|alchemists?|scriptori(um|a)|reigns?|reigned|tourney)\b|\bthrones?\b(?! of power)",
    re.IGNORECASE,
)


def every_enum() -> Iterator[type[StrEnum]]:
    for info in pkgutil.iter_modules(enum_package.__path__):
        module = importlib.import_module(f"{enum_package.__name__}.{info.name}")
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, StrEnum) and value.__module__ == module.__name__:
                yield value


def test_every_age_neutral_word_names_a_real_enum_value() -> None:
    known = {(kind.__name__, member.value) for kind in every_enum() for member in kind}
    assert sorted(set(AGE_NEUTRAL) - known) == []


def test_no_happening_names_an_institution_with_an_era_bound_word() -> None:
    assert sorted(key for key, spec in INCIDENT_KINDS.items() if spec.template and ERA_BOUND.search(spec.template)) == []


def test_every_value_a_happening_tells_fits_any_age() -> None:
    told = {fact.enum for spec in INCIDENT_KINDS.values() for fact in spec.facts if fact.value is FactValue.ENUM and fact.enum is not None}
    assert sorted(f"{kind.__name__}.{member.value}" for kind in told for member in kind if ERA_BOUND.search(spoken(member))) == []


def test_a_notable_clerk_comes_forward_as_a_clerk() -> None:
    names = {IncidentRole.SUBJECT: ["Somel"], IncidentRole.ORIGIN: ["Varnel"]}
    text = render_incident(INCIDENT_KINDS["births.notable"], names, {"social_class": SocialClass.SCRIBE, "role": MortalRole.SCRIBE})
    assert text == "Somel of Varnel came forward as a clerk."


def test_a_new_leader_comes_to_lead_what_it_rules() -> None:
    names = {IncidentRole.SUCCESSOR: ["Syrelhsel"], IncidentRole.SUBJECT: ["Veshwel Craft Association"]}
    text = render_incident(INCIDENT_KINDS["births.ruler"], names, {"role": MortalRole.RULER})
    assert text == "Syrelhsel came to lead Veshwel Craft Association."


def test_a_modern_faction_is_named_for_its_age() -> None:
    names = [plan.noun(TechnologyEra.INFORMATION) for plan in BLUEPRINTS]
    assert [name for name in names if ERA_BOUND.search(name)] == []
    craft = next(plan for plan in BLUEPRINTS if plan.subtype == "craft association")
    assert (craft.noun(TechnologyEra.MEDIEVAL), craft.noun(TechnologyEra.INFORMATION)) == ("Craft Guild", "Craft Association")


def test_generated_names_and_typed_labels_fit_any_age() -> None:
    words = [
        *(plan.subtype for plan in BLUEPRINTS),
        *(plan.members for plan in BLUEPRINTS),
        *(" ".join(pair) for pair in FACTION_KINDS.values()),
        *TRADITIONS.values(),
        *(word for pair in RULER_TITLES.values() for word in pair),
        *(word for roles in BASE_ROLES.values() for word in roles),
        *CLASS_ROLES.values(),
        *(word for roles in NOTABLE_ROLES.values() for role in roles for word in (role.suffix, role.subtype)),
        *RANK_WORDS.values(),
        *OWNER_LABELS.values(),
        *ESTATE_NAMES.values(),
        *(word for spec in SOCIAL_CLASSES.values() for word in (spec.singular, spec.plural)),
    ]
    assert sorted({word for word in words if ERA_BOUND.search(word)}) == []
