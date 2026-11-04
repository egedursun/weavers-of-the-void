from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.wars import WarSummary
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import (
    ArmourType,
    CaptiveFate,
    CommanderTrait,
    DefenderAction,
    OutcomeClass,
    ShieldType,
    SiegeAction,
    SpyCover,
    Stance,
    StarvationStage,
    Tactic,
    UnitFamily,
    UnitKind,
    WarAimKind,
)
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import BattleOutcome, SiegeStatus, WarSide


class UnitKindSpec(ApiModel):
    kind: UnitKind
    family: UnitFamily
    label: str
    melee: int
    missile: int
    defence: int
    speed: int
    mass: int
    cost: int
    upkeep: int
    armour: ArmourType
    shield: ShieldType
    terror: int


class StackView(ApiModel):
    id: int
    kind: UnitKind
    family: UnitFamily
    label: str
    count: int
    quality: int
    armour: ArmourType
    shield: ShieldType
    helmet: bool
    weapons: list[str]
    experience: int
    morale: int
    fatigue: int
    wounded: int
    condition: int


class MovementView(ApiModel):
    epoch: int
    season: int
    from_region: NodeRef | None
    to_region: NodeRef | None
    stance: Stance
    supply_days: int
    attrition: int
    note: str | None


class ArmyCard(ApiModel):
    army: NodeRef | None
    owner: NodeRef | None
    commander: NodeRef | None
    war_id: int | None
    size: int
    region: NodeRef | None
    target: NodeRef | None
    blockade: NodeRef | None
    stance: Stance
    doctrine: str
    supply_days: int
    supply_line: list[NodeRef]
    cohesion: int
    war_chest: int
    disease: int
    loot: int
    entrenchment: int
    forced_march: bool
    baggage: int
    locked: list[str]
    stacks: list[StackView]
    movements: list[MovementView]
    commander_traits: list[CommanderTrait]


class BattlePhaseView(ApiModel):
    position: int
    phase: str
    attacker_losses: int
    defender_losses: int
    summary: str | None
    details: dict[str, int | str]


class BattleReportView(ApiModel):
    id: int
    war_id: int
    epoch: int
    sequence: int
    record: NodeRef | None
    place: NodeRef | None
    winner: NodeRef | None
    loser: NodeRef | None
    outcome: BattleOutcome
    outcome_class: OutcomeClass | None
    gap: float
    siege_id: int | None
    weather: WeatherKind | None
    terrain: TerrainKind | None
    season_name: str | None
    year: int | None
    night: bool
    tactics_attacker: Tactic | None
    tactics_defender: Tactic | None
    casualties_by_kind: dict[str, int]
    winner_losses: int
    loser_losses: int
    phases: list[BattlePhaseView]


class SiegeTracker(ApiModel):
    id: int
    besieged: NodeRef | None
    besieger: NodeRef | None
    status: SiegeStatus
    started_epoch: int
    ended_epoch: int | None
    rounds: int
    walls_level: int
    breaches: int
    supplies: int
    water: int
    disease_inside: int
    disease_outside: int
    works: dict[str, int]
    sallies: int
    starvation: StarvationStage
    last_action: SiegeAction | None
    last_defence: DefenderAction | None


class AimView(ApiModel):
    id: int
    side: NodeRef | None
    kind: WarAimKind
    target: NodeRef | None
    achieved: int


class OccupationView(ApiModel):
    region: NodeRef | None
    occupier: NodeRef | None
    war_id: int | None
    since_epoch: int
    control: int
    resistance: int


class FrontView(ApiModel):
    first_region: NodeRef | None
    second_region: NodeRef | None
    since_epoch: int
    last_epoch: int


class CaptiveCohortView(ApiModel):
    id: int
    captor: NodeRef | None
    origin: NodeRef | None
    war_id: int | None
    count: int
    social_class: SocialClass
    fate: CaptiveFate
    since_epoch: int
    settled_epoch: int | None


class SideWeariness(ApiModel):
    entity: NodeRef | None
    side: WarSide
    weariness: int


class WarRoomView(ApiModel):
    war: WarSummary
    weariness: list[SideWeariness]
    aims: list[AimView]
    armies: list[ArmyCard]
    sieges: list[SiegeTracker]
    fronts: list[FrontView]
    occupations: list[OccupationView]
    captives: list[CaptiveCohortView]
    battles: list[BattleReportView]


class SpyNetworkView(ApiModel):
    id: int
    owner: NodeRef | None
    target: NodeRef | None
    agents: int
    depth: int
    exposure: int
    cover: SpyCover
    spymaster: NodeRef | None
    intel: int
    last_operation: str | None
    last_epoch: int | None
    since_epoch: int


class MilitaryOverview(ApiModel):
    armies: list[ArmyCard]
    captives_held: list[CaptiveCohortView]
    captives_lost: list[CaptiveCohortView]
    networks: list[SpyNetworkView]
    watched_by: list[SpyNetworkView]
    occupying: list[OccupationView]
    occupied: list[OccupationView]
    commander_traits: list[CommanderTrait]
