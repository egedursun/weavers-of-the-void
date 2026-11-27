from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule, ProcessClock, ProcessGroup, StepAction, StepLocus

NodeFilter = NodeKind | EntityType


@dataclass(frozen=True)
class RoleSpec:
    role: IncidentRole
    accepts: frozenset[NodeFilter] = frozenset()
    required: bool = True
    many: bool = False


@dataclass(frozen=True)
class FactSpec:
    key: str
    value: FactValue
    unit: FactUnit | None = None
    enum: type[StrEnum] | None = None
    required: bool = True
    many: bool = False


@dataclass(frozen=True)
class IncidentKindSpec:
    key: str
    group: ProcessGroup
    template: str
    roles: tuple[RoleSpec, ...] = ()
    facts: tuple[FactSpec, ...] = ()
    steps: frozenset[StepAction] = frozenset()
    place: PlaceRule = PlaceRule.WHEN_KNOWN
    place_kind: StepLocus | None = None
    clock: ProcessClock = ProcessClock.PHASE
    terms: bool = False
    direct: bool = False
    collection: CollectionKind | None = None
    feed: FeedCategory | None = None
    chronicle_kind: ChronicleKind = ChronicleKind.WORLD
    magnitude: int = 0
    draft: bool = False
    told: bool = True
    legacy: bool = False
    repeatable: bool = False
    open_facts: bool = False
    enum_suffix: type[StrEnum] | None = field(default=None, compare=False)

    @property
    def family(self) -> str:
        return self.key.split(".", 1)[0]

    def role(self, role: IncidentRole) -> RoleSpec | None:
        return next((spec for spec in self.roles if spec.role is role), None)

    def fact(self, key: str) -> FactSpec | None:
        return next((spec for spec in self.facts if spec.key == key), None)


def per_value(prefix: str, values: type[StrEnum], spec: IncidentKindSpec, told: Mapping[Any, str] | None = None) -> tuple[IncidentKindSpec, ...]:
    return tuple(
        replace(spec, key=f"{prefix}{member.value}", enum_suffix=values, template=told[member] if told is not None else spec.template) for member in values
    )
