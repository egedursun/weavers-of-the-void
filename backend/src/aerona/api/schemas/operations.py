from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.integrity import SectionState
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.operations import (
    CarrierKind,
    CrewStation,
    EchelonLevel,
    EchelonOrder,
    ExpeditionEvent,
    ExpeditionGround,
    ExpeditionRole,
    ExpeditionStatus,
    PointOfSail,
    QuirkKind,
    ResolveKind,
    ShotKind,
)
from aerona.domain.enums.vehicles import VehicleSection


class EchelonView(ApiModel):
    id: int
    owner: NodeRef
    army: NodeRef | None
    parent_id: int | None
    level: EchelonLevel
    name: str
    commander: NodeRef | None
    hq: NodeRef | None
    staff: int
    command_range: int
    command_points: int
    points_spent: int
    order: EchelonOrder
    in_range: bool
    formed_epoch: int
    stacks: int
    locked: list[str]


class StackPlacementView(ApiModel):
    id: int
    unit_kind: UnitKind
    count: int
    echelon_id: int | None
    locked: list[str]


class OperationView(ApiModel):
    army: NodeRef
    offensive_seasons: int
    need: int
    delivered: int
    organisation: int
    culminated: bool
    culminated_epoch: int | None
    pause_seasons: int
    foresight: int
    standing: bool
    updated_epoch: int
    locked: list[str]


class SupplyFlowView(ApiModel):
    id: int
    epoch: int
    season: int
    owner: NodeRef
    army: NodeRef
    depot_id: int | None
    produced: int
    shipped: int
    lost: int
    delivered: int
    need: int
    throughput: int
    locked: list[str]


class DepotView(ApiModel):
    id: int
    owner: NodeRef
    region: NodeRef | None
    structure: NodeRef | None
    supplies: int
    capacity: int
    field: bool
    cut: bool
    founded_epoch: int
    locked: list[str]


class TransportView(ApiModel):
    id: int
    owner: NodeRef
    depot_id: int | None
    transport_kind: CarrierKind
    count: int
    capacity: int
    condition: int
    locked: list[str]


class TheatreView(ApiModel):
    id: int
    owner: NodeRef
    war_id: int
    war: NodeRef | None
    front: NodeRef | None
    marshal: NodeRef | None
    priority: int
    believed_threat: int
    true_threat: int
    reserves: int
    levies: int
    transport: int
    misjudged: bool
    updated_epoch: int
    locked: list[str]


class WarOptionView(ApiModel):
    war_id: int
    war: NodeRef | None
    enemy: NodeRef


class AdmiraltyView(ApiModel):
    polity: NodeRef
    admiral: NodeRef | None
    budget_share: int
    requested: int
    influence: int
    tonnage: int
    limit_tonnage: int | None
    concealed: int
    commissioned: int
    updated_epoch: int
    locked: list[str]


class ShipSectionView(ApiModel):
    section: VehicleSection
    state: SectionState
    condition: int


class ShipView(ApiModel):
    vessel: NodeRef
    heading: int
    wind_from: int
    point_of_sail: PointOfSail
    tacks: int
    shot: ShotKind
    leak: int
    fire: int
    magazine: bool
    rate_of_fire: int
    rower_fatigue: int
    raked: int
    struck: bool
    prize_of: NodeRef | None
    prize_crew: int
    prize_money: int
    hull_condition: int
    crew_total: int
    sections: list[ShipSectionView]
    updated_epoch: int
    locked: list[str]


class CrewView(ApiModel):
    station: CrewStation
    count: int
    skill: int
    locked: list[str]


class QuirkView(ApiModel):
    id: int
    quirk_kind: QuirkKind
    source: NodeRef | None
    expedition_id: int | None
    strength: int
    gained_epoch: int
    locked: list[str]


class ExpeditionMemberView(ApiModel):
    id: int
    mortal: NodeRef
    role: ExpeditionRole
    stress: int
    resolve: ResolveKind
    cold: int
    wet: int
    hunger: int
    fatigue: int
    fallen: bool
    locked: list[str]


class ExpeditionLogView(ApiModel):
    id: int
    epoch: int
    leg: int
    event: ExpeditionEvent
    member: NodeRef | None
    provisions_used: int
    light_used: int
    stress: int
    resolve: ResolveKind | None
    quirk: QuirkKind | None
    locked: list[str]


class ExpeditionView(ApiModel):
    id: int
    name: str
    leader: NodeRef | None
    sponsor: NodeRef | None
    target: NodeRef | None
    ground: ExpeditionGround
    status: ExpeditionStatus
    legs_done: int
    legs_total: int
    provisions: int
    light: int
    tools: int
    medicine: int
    darkness: int
    danger: int
    found: int
    started_epoch: int
    ended_epoch: int | None
    missing_roles: list[ExpeditionRole]
    members: list[ExpeditionMemberView]
    log: list[ExpeditionLogView]
    locked: list[str]


class OperationsNodeView(ApiModel):
    node: NodeRef
    echelons: list[EchelonView]
    stacks: list[StackPlacementView]
    operation: OperationView | None
    flows: list[SupplyFlowView]
    depots: list[DepotView]
    transport: list[TransportView]
    theatres: list[TheatreView]
    wars: list[WarOptionView]
    admiralty: AdmiraltyView | None
    ship: ShipView | None
    crews: list[CrewView]
    crew_stations: list[CrewStation]
    quirks: list[QuirkView]
    expeditions: list[ExpeditionView]
