from typing import Any

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.military import (
    CasualtyFate,
    FeudParty,
    FeudStatus,
    Formation,
    HullClass,
    MoraleState,
    PeaceTermKind,
    TargetClass,
    UnitKind,
    VesselArmament,
    VesselStatus,
)


class RecordColumnView(ApiModel):
    name: str
    kind: str
    options: list[str]
    nullable: bool
    required: bool


class RecordRowView(ApiModel):
    id: int
    values: dict[str, Any]
    locked: list[str]
    refs: dict[str, NodeRef]


class RecordTableView(ApiModel):
    kind: str
    label: str
    creatable: bool
    deletable: bool
    scope: str | None
    columns: list[RecordColumnView]
    rows: list[RecordRowView]


class BattleStackView(ApiModel):
    side: NodeRef | None
    army: NodeRef | None
    kind: UnitKind
    label: str
    start: int
    lost: int
    wounded: int
    routed: bool
    killed: int
    walking: int
    stretcher: int
    captured: int
    missing: int
    deserted: int
    reserve: bool
    organisation: int
    ammunition_spent: int
    formation: Formation | None
    morale_state: MoraleState | None
    target_class: TargetClass | None


class BattleCasualtyView(ApiModel):
    mortal: NodeRef | None
    side: NodeRef | None
    fate: CasualtyFate
    harm: int
    note: str | None


class BattleDepthView(ApiModel):
    battle_id: int
    stacks: list[BattleStackView]
    casualties: list[BattleCasualtyView]
    tactic_factors: dict[str, float]
    morale: dict[str, dict[str, int]]
    magic: dict[str, int]


class HullSpecView(ApiModel):
    hull: HullClass
    label: str
    speed: int
    range: int
    cargo: int
    crew: int
    seaworthiness: int
    slots: int
    armament: list[VesselArmament]
    sky: bool
    living: bool
    strangeness: int


class VesselView(ApiModel):
    vessel: NodeRef | None
    owner: NodeRef | None
    captain: NodeRef | None
    home_port: NodeRef | None
    region: NodeRef | None
    fleet: NodeRef | None
    legend: NodeRef | None
    hull: HullSpecView
    hull_material: str | None
    fabric_material: str | None
    condition: int
    armament: list[VesselArmament]
    seaworthiness: int
    cargo_capacity: int
    crew: int
    seamanship: int
    renown: int
    strangeness: int
    status: VesselStatus
    voyages: int
    locked: list[str]


class FeudView(ApiModel):
    id: int
    first: NodeRef | None
    second: NodeRef | None
    party: FeudParty
    intensity: int
    grievance: int
    generations: int
    status: FeudStatus
    cause: str | None
    since_epoch: int
    last_epoch: int | None
    last_action: str | None
    ended_epoch: int | None
    grief: int
    locked: list[str]


class PeaceTermView(ApiModel):
    id: int
    war_id: int
    kind: PeaceTermKind
    beneficiary: NodeRef | None
    obligor: NodeRef | None
    treaty: NodeRef | None
    params: dict[str, int | str | bool]
    epoch: int
    note: str | None
