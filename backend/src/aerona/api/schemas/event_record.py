from datetime import datetime

from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import (
    FactUnit,
    IncidentTier,
    InstrumentKind,
    ProcessGroup,
    RumourDistortion,
    StepAction,
    StepLocus,
    StepOutcome,
    StepState,
    WitnessMode,
)


class EventMomentRecord(ApiModel):
    epoch: int
    year: int | None
    season: int | None
    day: int | None
    hour: int | None


class EventParticipantRecord(ApiModel):
    node_id: int
    name: str | None
    role: IncidentRole
    position: int
    witness_mode: WitnessMode | None
    fidelity: int | None


class EventFactRecord(ApiModel):
    id: int
    key: str
    position: int
    node_id: int | None
    node_name: str | None
    number: float | None
    unit: FactUnit | None
    enum_name: str | None
    enum_value: str | None
    name: str | None


class EventTermRecord(ApiModel):
    position: int
    term: str
    op: ModifierOp
    amount: float
    source_node_id: int | None
    source_name: str | None
    source_incident_id: int | None
    fact_key: str | None


class EventStepStateRecord(ApiModel):
    node_id: int
    node_name: str | None
    state: StepState


class EventStepRecord(ApiModel):
    id: int
    incident_id: int
    position: int
    round: int | None
    parent_step_id: int | None
    moment: EventMomentRecord
    actor_node_id: int | None
    actor_name: str | None
    target_node_id: int | None
    target_name: str | None
    action: StepAction
    instrument_kind: InstrumentKind
    instrument_node_id: int | None
    instrument_name: str | None
    instrument_key: str | None
    locus_kind: StepLocus
    locus_key: str | None
    locus_node_id: int | None
    locus_name: str | None
    damage_type: DamageType | None
    amount: float | None
    unit: FactUnit | None
    outcome: StepOutcome | None
    record_table: str | None
    record_key: str | None
    states: list[EventStepStateRecord] = Field(default_factory=list)


class EventChangeRecord(ApiModel):
    id: int
    moment: EventMomentRecord
    table_name: str
    row_key: str
    node_id: int | None
    node_name: str | None
    operation: LedgerOperation
    field: str | None
    before_number: float | None
    after_number: float | None
    before_text: str | None
    after_text: str | None
    before_node_id: int | None
    before_node_name: str | None
    after_node_id: int | None
    after_node_name: str | None
    actor_kind: ActorKind
    actor_node_id: int | None
    actor_name: str | None
    phase: str | None
    incident_id: int | None
    step_id: int | None
    terms: list[EventTermRecord] = Field(default_factory=list)
    author_account_id: int | None = None
    author_name: str | None = None
    changed_at: datetime | None = None


class EventRumourDistortionRecord(ApiModel):
    id: int
    position: int
    distortion: RumourDistortion
    role: IncidentRole | None
    fact_key: str | None
    step_id: int | None
    told_node_id: int | None
    told_name: str | None
    told_number: float | None
    told_enum_value: str | None
    told_year: int | None
    told_incident_id: int | None
    told_action: StepAction | None
    told_outcome: StepOutcome | None
    epoch: int
    locked: list[str]


class EventRumourRecord(ApiModel):
    id: int
    carrier_id: int
    carrier_name: str | None
    source_id: int | None
    source_name: str | None
    fidelity: int
    hops: int
    epoch: int
    distortions: list[EventRumourDistortionRecord] = Field(default_factory=list)


class EventLinkRecord(ApiModel):
    id: int
    kind: str
    epoch: int
    year: int | None
    text: str | None


class EventAccountView(ApiModel):
    id: int
    kind: str
    family: str
    group: ProcessGroup | None
    known: bool
    name: str | None
    name_language_id: int | None
    name_language_name: str | None
    moment: EventMomentRecord
    world_id: int | None
    place_id: int | None
    place_name: str | None
    origin_id: int | None
    origin_name: str | None
    destination_id: int | None
    destination_name: str | None
    tier: IncidentTier
    locked: list[str]
    magnitude: int
    chronicle_id: int | None
    line: str | None
    retold: str | None
    note: str | None
    thread_id: int | None
    participants: list[EventParticipantRecord]
    witnesses: list[EventParticipantRecord]
    facts: list[EventFactRecord]
    steps: list[EventStepRecord]
    terms: list[EventTermRecord]
    changes: list[EventChangeRecord]
    rumours: list[EventRumourRecord]
    causes: list[EventLinkRecord]
    effects: list[EventLinkRecord]


class NodeHistoryEntry(ApiModel):
    incident_id: int
    kind: str
    group: ProcessGroup | None
    moment: EventMomentRecord
    roles: list[IncidentRole]
    line: str | None
    place_id: int | None
    place_name: str | None
    tier: IncidentTier
    facts: int
    steps: int
    changes: int


class NodeHistoryView(ApiModel):
    node_id: int
    offset: int
    limit: int
    total_incidents: int
    incidents: list[NodeHistoryEntry]
    total_steps: int
    steps: list[EventStepRecord]
    total_changes: int
    changes: list[EventChangeRecord]
    kinds: list[str]
    roles: list[IncidentRole]


class StateAtFieldRecord(ApiModel):
    field: str
    then: str | None
    now: str | None
    changed: bool


class StateAtRowRecord(ApiModel):
    table_name: str
    row_key: str
    existed: bool
    exists_now: bool
    fields: list[StateAtFieldRecord]


class StateAtView(ApiModel):
    epoch: int
    year: int | None
    season: int | None
    day: int | None
    hour: int | None
    node_id: int | None
    table_name: str | None
    offset: int
    limit: int
    total: int
    rows: list[StateAtRowRecord]


class FactSearchHit(ApiModel):
    incident_id: int
    kind: str
    epoch: int
    year: int | None
    line: str | None
    fact_key: str | None
    node_id: int | None
    node_name: str | None
    number: float | None
    unit: FactUnit | None
    enum_name: str | None
    enum_value: str | None
    name: str | None
    step_action: StepAction | None
    instrument_kind: InstrumentKind | None


class FactSearchView(ApiModel):
    offset: int
    limit: int
    total: int
    hits: list[FactSearchHit]
