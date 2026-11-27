import re

from aerona.catalog.incident_kinds.newborns import NEWBORN_KINDS
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.domain.enums.modifier import IncidentRole

BORN = re.compile(r"\bborn\b")


def has_child(key: str) -> bool:
    return any(role.role is IncidentRole.CHILD for role in INCIDENT_KINDS[key].roles)


def test_every_newborn_kind_exists_and_names_its_child() -> None:
    assert sorted(key for key in NEWBORN_KINDS if key not in INCIDENT_KINDS or not has_child(key)) == []


def test_only_a_newborn_kind_tells_its_child_as_born() -> None:
    told = sorted(key for key, spec in INCIDENT_KINDS.items() if not spec.legacy and has_child(key) and key not in NEWBORN_KINDS and BORN.search(spec.template))
    assert told == []
