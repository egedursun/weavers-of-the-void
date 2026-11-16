from typing import Any

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.integrity import Criticality, SectionHazard
from aerona.domain.enums.military import (
    CasualtyFate,
    FeudLevel,
    FeudParty,
    FeudStatus,
    Formation,
    MoraleState,
    PeaceTermKind,
    TargetClass,
    UnitKind,
    VesselArmament,
    VesselStatus,
)
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import MountKind, Propulsion, VehicleDomain, VehicleFamily, VehicleFrame, VehicleSection, VehicleSize


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


class FrameSectionView(ApiModel):
    section: VehicleSection
    function: DesignComponentKind
    criticality: Criticality
    share: int
    exposure: int
    hazard: SectionHazard
    neighbours: list[VehicleSection]


class FrameSpecView(ApiModel):
    frame: VehicleFrame
    label: str
    domain: VehicleDomain
    family: VehicleFamily
    propulsion: Propulsion
    size: VehicleSize
    speed: int
    range: int
    cargo: int
    crew: int
    troops: int
    endurance: int
    armour: int
    structure: int
    slots: int
    mounts: list[MountKind]
    sections: list[FrameSectionView]
    armament: list[VesselArmament]
    branch: KnowledgeBranch | None
    level: int
    tier: int | None
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
    frame: FrameSpecView
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
    level: FeudLevel
    mediator: NodeRef | None
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
