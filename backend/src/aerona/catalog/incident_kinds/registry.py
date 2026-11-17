from collections.abc import Iterable
from types import MappingProxyType

from aerona.catalog.incident_kinds.authored import KINDS as AUTHORED
from aerona.catalog.incident_kinds.g01_single_combat import KINDS as SINGLE_COMBAT
from aerona.catalog.incident_kinds.g02_battles import KINDS as BATTLES
from aerona.catalog.incident_kinds.g03_vessels import KINDS as VESSELS
from aerona.catalog.incident_kinds.g04_body import KINDS as BODY
from aerona.catalog.incident_kinds.g05_making import KINDS as MAKING
from aerona.catalog.incident_kinds.g06_exchange import KINDS as EXCHANGE
from aerona.catalog.incident_kinds.g07_law import KINDS as LAW
from aerona.catalog.incident_kinds.g08_diplomacy import KINDS as DIPLOMACY
from aerona.catalog.incident_kinds.g09_faith import KINDS as FAITH
from aerona.catalog.incident_kinds.g10_movement import KINDS as MOVEMENT
from aerona.catalog.incident_kinds.g11_social import KINDS as SOCIAL
from aerona.catalog.incident_kinds.g12_knowledge import KINDS as KNOWLEDGE
from aerona.catalog.incident_kinds.g13_nature import KINDS as NATURE
from aerona.catalog.incident_kinds.g14_cosmos import KINDS as COSMOS
from aerona.catalog.incident_kinds.g15_gods import KINDS as GODS
from aerona.catalog.incident_kinds.g16_peoples import KINDS as PEOPLES
from aerona.catalog.incident_kinds.phases import KINDS as PHASES
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.catalog.incident_kinds.tellings import KINDS as TELLINGS

GROUP_KINDS: tuple[tuple[IncidentKindSpec, ...], ...] = (
    SINGLE_COMBAT,
    BATTLES,
    VESSELS,
    BODY,
    MAKING,
    EXCHANGE,
    LAW,
    DIPLOMACY,
    FAITH,
    MOVEMENT,
    SOCIAL,
    KNOWLEDGE,
    NATURE,
    COSMOS,
    GODS,
    PEOPLES,
    PHASES,
    AUTHORED,
    TELLINGS,
)


class DuplicateKindError(ValueError):
    pass


def declared(kinds: Iterable[IncidentKindSpec]) -> MappingProxyType[str, IncidentKindSpec]:
    found: dict[str, IncidentKindSpec] = {}
    for spec in kinds:
        if spec.key in found:
            raise DuplicateKindError(f"the incident kind {spec.key!r} is declared twice")
        found[spec.key] = spec
    return MappingProxyType(found)


INCIDENT_KINDS = declared(spec for kinds in GROUP_KINDS for spec in kinds)
