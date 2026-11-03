from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource
from aerona.engine.interconnect.registry import Exposure, Subsystem


class MechanicRecord(ApiModel):
    key: str
    spec_item: str
    title: str
    subsystem: Subsystem
    phases: list[str]
    surfaces: list[str]
    backfill: str
    fields: list[str]
    flows: list[str]
    exposure: Exposure
    tools: list[str]
    couplings: list[Subsystem]


class ModifierRecord(ApiModel):
    id: int
    key: str
    op: ModifierOp
    magnitude: float
    source_kind: ModifierSource
    source_subsystem: Subsystem
    source_node_id: int | None
    source_name: str | None
    reason_key: str
    reason: str
    stacking_group: str | None
    start_epoch: int
    end_epoch: int | None
    decay_pct: int | None


class EffectiveValue(ApiModel):
    key: str
    base: float
    value: float
    applied: list[int]
    ignored: list[int]


class GuardRecord(ApiModel):
    id: int
    key: str
    end_epoch: int | None


class IncidentRecord(ApiModel):
    id: int
    kind: str
    epoch: int
    year: int | None
    role: IncidentRole
    magnitude: int
    cause_incident_id: int | None
    chronicle_id: int | None
    text: str | None
    note: str | None
    thread_id: int | None
    causes: list[str]
    consequences: list[int]


class ActingMechanic(ApiModel):
    key: str
    title: str
    subsystem: Subsystem
    spec_item: str
    fields: list[str]
    reads: list[str]
    writes: list[str]
    affects: list[Subsystem]
    suppressed: bool
    last_incident_id: int | None
    last_text: str | None
    last_epoch: int | None


class NodeMechanicsView(ApiModel):
    node_id: int
    epoch: int
    acting: list[ActingMechanic]
    modifiers: list[ModifierRecord]
    effective: list[EffectiveValue]
    pins: list[GuardRecord]
    suppressions: list[GuardRecord]
    incidents: list[IncidentRecord]
