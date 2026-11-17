from collections.abc import Iterable
from enum import StrEnum

from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, NodeFilter, RoleSpec
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule, ProcessClock, ProcessGroup, StepAction


def one(role: IncidentRole, *accepts: NodeFilter) -> RoleSpec:
    return RoleSpec(role, frozenset(accepts))


def maybe(role: IncidentRole, *accepts: NodeFilter) -> RoleSpec:
    return RoleSpec(role, frozenset(accepts), required=False)


def some(role: IncidentRole, *accepts: NodeFilter, required: bool = True) -> RoleSpec:
    return RoleSpec(role, frozenset(accepts), required=required, many=True)


def amount(key: str, unit: FactUnit, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NUMBER, unit, required=required)


def chosen(key: str, enum: type[StrEnum], *, required: bool = True, many: bool = False) -> FactSpec:
    return FactSpec(key, FactValue.ENUM, enum=enum, required=required, many=many)


def node(key: str, *, required: bool = True, many: bool = False) -> FactSpec:
    return FactSpec(key, FactValue.NODE, required=required, many=many)


def named(key: str, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NAME, required=required)


def happening(
    key: str,
    group: ProcessGroup,
    template: str,
    *,
    roles: Iterable[RoleSpec],
    facts: Iterable[FactSpec] = (),
    steps: Iterable[StepAction] = (),
    place: PlaceRule = PlaceRule.WHEN_KNOWN,
    clock: ProcessClock = ProcessClock.SEASON,
    kind: ChronicleKind = ChronicleKind.WORLD,
    feed: FeedCategory | None = None,
    magnitude: int = 0,
    terms: bool = False,
    direct: bool = False,
) -> IncidentKindSpec:
    return IncidentKindSpec(
        key,
        group,
        template,
        roles=tuple(roles),
        facts=tuple(facts),
        steps=frozenset(steps),
        place=place,
        clock=clock,
        terms=terms,
        direct=direct,
        feed=feed,
        chronicle_kind=kind,
        magnitude=magnitude,
    )
