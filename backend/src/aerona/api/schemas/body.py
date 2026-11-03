from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.body import (
    BodyFunction,
    BodyPlan,
    BodyReading,
    BodyRegion,
    Capacity,
    ConditionKind,
    DamageType,
    HarmCause,
    InjuryKind,
    InjuryState,
    MaimedKind,
    MedicineTier,
)
from aerona.domain.enums.material import MaterialKind


class ProsthesisView(ApiModel):
    id: int
    injury_id: int
    part: str
    material: MaterialKind
    quality: int
    restored_pct: int
    item_entity_id: int | None
    item_name: str | None
    maker_node_id: int | None
    maker_name: str | None
    epoch: int


class InjuryView(ApiModel):
    id: int
    part: str
    part_label: str
    kind: InjuryKind
    damage_type: DamageType
    severity: int
    state: InjuryState
    function_loss: int
    cause_kind: HarmCause
    cause_node_id: int | None
    cause_name: str | None
    cause_link: str | None
    event_entity_id: int | None
    event_name: str | None
    epoch: int
    year: int | None
    treated_by_node_id: int | None
    treated_by_name: str | None
    visible: bool
    infected_epochs: int
    healed_epoch: int | None
    prosthesis: ProsthesisView | None


class ConditionView(ApiModel):
    id: int
    kind: ConditionKind
    severity: int
    part: str | None
    source: HarmCause
    source_node_id: int | None
    source_name: str | None
    source_link: str | None
    since_epoch: int
    ended_epoch: int | None
    visible: bool


class PartView(ApiModel):
    key: str
    label: str
    region: BodyRegion
    functions: list[BodyFunction]
    severable: bool
    internal: bool
    vital: bool
    loss: int
    state: InjuryState | None
    prosthesis: MaterialKind | None


class CapacityView(ApiModel):
    key: Capacity
    factor: int
    value: int
    base: int
    locked: bool


class FunctionView(ApiModel):
    key: BodyFunction
    level: int


class ArmourView(ApiModel):
    head: int
    torso: int
    limbs: int


class BodyView(ApiModel):
    node_id: int
    name: str
    bearer_kind: str
    alive: bool
    plan: BodyPlan
    traits: list[BodyFunction]
    hp: int | None
    hp_max: int | None
    pain: int
    fingers: int
    armour: ArmourView
    capacities: list[CapacityView]
    functions: list[FunctionView]
    parts: list[PartView]
    injuries: list[InjuryView]
    conditions: list[ConditionView]
    locked: list[str]
    patients_healed: int
    patients_lost: int
    medicine: MedicineTier
    healer_id: int | None
    healer_name: str | None
    healer_skill: int | None
    presence_pct: int
    people_id: int | None
    people_name: str | None
    reading: BodyReading | None
    wholeness_required: bool
    updated_epoch: int


class BodyCustomsView(ApiModel):
    people_id: int
    reading: BodyReading
    derived_reading: BodyReading
    wholeness_required: bool
    seer_eye: bool
    scar_festivals: bool
    pension: bool
    tradition_id: int | None
    tradition_name: str | None
    locked: list[str]
    maimed_rulers: int


class CohortView(ApiModel):
    kind: MaimedKind
    count: int
    veterans: int
    updated_epoch: int


class MaimedView(ApiModel):
    community_id: int
    population: int
    total: int
    veterans: int
    share_pct: int
    labour_pct: int
    war_appetite_pct: int
    healer_demand_pct: int
    pension: bool
    reading: BodyReading | None
    people_id: int | None
    people_name: str | None
    cohorts: list[CohortView]
