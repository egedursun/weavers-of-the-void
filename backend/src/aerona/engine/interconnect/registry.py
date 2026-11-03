from dataclasses import dataclass, field
from enum import StrEnum


class Subsystem(StrEnum):
    CORE = "core"
    BODY = "body"
    MIND = "mind"
    SOCIAL = "social"
    HOUSEHOLD = "household"
    DEMOGRAPHY = "demography"
    ECONOMY = "economy"
    POLITY = "polity"
    LAW = "law"
    INTRIGUE = "intrigue"
    COMMUNICATION = "communication"
    WAR = "war"
    FAITH = "faith"
    MAGIC = "magic"
    KNOWLEDGE = "knowledge"
    CULTURE = "culture"
    LANGUAGE = "language"
    ECOLOGY = "ecology"
    ENVIRONMENT = "environment"
    GODS = "gods"
    COSMOS = "cosmos"


class Exposure(StrEnum):
    NONE = "none"
    CONTEXT = "context"
    TOOL = "tool"


@dataclass(frozen=True)
class Surface:
    drawer: str | None = None
    layer: str | None = None
    chart: str | None = None

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key in (self.drawer, self.layer, self.chart) if key)


class EdgeKind(StrEnum):
    MODIFIER = "modifier"
    RULE_SWITCH = "rule_switch"
    FLOW = "flow"
    TRIGGER = "trigger"


@dataclass(frozen=True)
class Coupling:
    target: Subsystem
    carrier: str
    kind: EdgeKind = EdgeKind.FLOW
    rule_key: str | None = None


@dataclass(frozen=True)
class Edge:
    source: Subsystem
    target: Subsystem
    carrier: str
    rule_key: str | None
    kind: EdgeKind
    writer: str
    reader: str | None = None


@dataclass(frozen=True)
class Mechanic:
    key: str
    spec_item: str
    title: str
    subsystem: Subsystem
    phases: tuple[str, ...]
    surface: Surface
    backfill: str
    templates: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    flows: tuple[str, ...] = ()
    exposure: Exposure = Exposure.NONE
    tools: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    couplings: tuple[Coupling, ...] = field(default_factory=tuple)


MECHANICS: dict[str, Mechanic] = {}


def register(mechanic: Mechanic) -> Mechanic:
    if mechanic.key in MECHANICS and MECHANICS[mechanic.key] != mechanic:
        raise ValueError(f"Mechanic {mechanic.key} is registered twice with different descriptors.")
    MECHANICS[mechanic.key] = mechanic
    return mechanic


def mechanic_keys_for_phase(phase_name: str) -> frozenset[str]:
    return frozenset({phase_name, *(mechanic.key for mechanic in MECHANICS.values() if phase_name in mechanic.phases)})


def suppression_key(mechanic_key: str) -> str:
    return f"mechanic:{mechanic_key}"
