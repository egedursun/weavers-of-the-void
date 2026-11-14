from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.sacred import (
    AfterlifeModel,
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    DivinationValidity,
    ForesightSource,
    ForesightStatus,
    GeniusLocusKind,
    MillenarianStage,
    MysticState,
    OmenVerdict,
    PetitionKind,
    PetitionStatus,
    SacramentKind,
    SacramentProtection,
    SpiritOffence,
    TheodicyCause,
    TheodicyResolution,
    VisionKind,
)


class GeniusView(ApiModel):
    spirit: NodeRef
    place: NodeRef | None
    community: NodeRef | None
    kind: GeniusLocusKind
    temperament: int
    contentment: int
    offerings: int
    owed: int
    favour: int
    offended: SpiritOffence | None
    last_offering_epoch: int | None
    bound_epoch: int
    locked: list[str]


class SpiritOfficeView(ApiModel):
    spirit: NodeRef
    rank: BureauRank
    superior: NodeRef | None
    overseer: NodeRef | None
    jurisdiction: NodeRef | None
    merit: int
    corruption: int
    resolved: int
    neglected: int
    dismissed: bool
    appointed_epoch: int
    locked: list[str]


class PetitionView(ApiModel):
    id: int
    petitioner: NodeRef
    office: NodeRef
    kind: PetitionKind
    defendant: NodeRef | None
    bribe: int
    status: PetitionStatus
    filed_epoch: int
    due_epoch: int
    resolved_epoch: int | None
    appealed_to: NodeRef | None
    locked: list[str]


class VisionView(ApiModel):
    id: int
    epoch: int
    kind: VisionKind
    sender: NodeRef | None
    genuine: bool
    awe: int
    locked: list[str]


class MysticView(ApiModel):
    mortal: NodeRef
    state: MysticState
    visions: int
    genuine_visions: int
    followers: int
    answered_by: NodeRef | None
    cult: NodeRef | None
    founded: NodeRef | None
    reverence: int
    persecution: int
    since_epoch: int
    last_vision_epoch: int | None
    history: list[VisionView]
    locked: list[str]


class MillenarianView(ApiModel):
    id: int
    settlement: NodeRef
    cult: NodeRef | None
    prophet: NodeRef | None
    prophecy: NodeRef | None
    movement_id: int | None
    stage: MillenarianStage
    end_epoch: int
    members: int
    conviction: int
    given_up: int
    idle_share: int
    attacks: int
    dates_set: int
    sect: NodeRef | None
    since_epoch: int
    ended_epoch: int | None
    locked: list[str]


class FaithCrisisView(ApiModel):
    id: int
    cult: NodeRef
    community: NodeRef
    god: NodeRef | None
    cause: TheodicyCause
    suffering: int
    answered: bool
    resolution: TheodicyResolution
    theologian: NodeRef | None
    started_epoch: int
    resolved_epoch: int | None
    locked: list[str]


class TeachingView(ApiModel):
    cult: NodeRef
    kind: SacramentKind
    protection: SacramentProtection
    strength: int
    since_epoch: int
    locked: list[str]


class SacramentView(ApiModel):
    id: int
    mortal: NodeRef
    kind: SacramentKind
    cult: NodeRef | None
    priest: NodeRef | None
    epoch: int
    missed: bool
    locked: list[str]


class TaughtAfterlifeView(ApiModel):
    cult: NodeRef
    model: AfterlifeModel
    aligned: bool
    aligned_by: NodeRef | None
    shocks: int
    testimonies: int
    doubt: int
    updated_epoch: int
    locked: list[str]


class FaithClimateView(ApiModel):
    community: NodeRef
    piety_drift: int
    literacy_pull: int
    science_pull: int
    prosperity_pull: int
    city_pull: int
    silence_pull: int
    disaster_push: int
    miracle_push: int
    war_push: int
    dominion_push: int
    silent_epochs: int
    godless: bool
    updated_epoch: int
    locked: list[str]


class DivinationSystemView(ApiModel):
    id: int
    people: NodeRef
    kind: DivinationKind
    validity: DivinationValidity
    trust: int
    diviners: int
    founded_epoch: int
    locked: list[str]


class OmenReadingView(ApiModel):
    id: int
    system_id: int
    diviner: NodeRef | None
    client: NodeRef | None
    question: DivinationQuestion
    verdict: OmenVerdict
    true_verdict: OmenVerdict
    heeded: bool
    swayed_by: NodeRef | None
    epoch: int
    locked: list[str]


class ForesightView(ApiModel):
    id: int
    seer: NodeRef
    subject: NodeRef | None
    predicate: ProphecyPredicate
    horizon: int
    due_epoch: int
    certainty: int
    source: ForesightSource
    divination_id: int | None
    status: ForesightStatus
    checked_epoch: int | None
    made_epoch: int
    locked: list[str]


class ForecastModelView(ApiModel):
    id: int
    order: NodeRef
    subject: NodeRef | None
    archive: int
    accuracy: int
    forecast_psi: int
    actual_psi: int
    plan_id: int | None
    disruption: int
    disrupted_by: NodeRef | None
    built_epoch: int
    horizon: int
    locked: list[str]


class FeedingView(ApiModel):
    emotion: Emotion
    weight: int
    harvested: int
    epoch: int
    locked: list[str]


class HarvestView(ApiModel):
    id: int
    epoch: int
    emotion: Emotion
    count: int
    essence: int


class SacredNodeView(ApiModel):
    node: NodeRef
    spirits: list[GeniusView]
    offices: list[SpiritOfficeView]
    petitions: list[PetitionView]
    mystic: MysticView | None
    mystics: list[MysticView]
    movements: list[MillenarianView]
    crises: list[FaithCrisisView]
    teachings: list[TeachingView]
    sacraments: list[SacramentView]
    afterlives: list[TaughtAfterlifeView]
    climate: FaithClimateView | None
    systems: list[DivinationSystemView]
    readings: list[OmenReadingView]
    foresights: list[ForesightView]
    models: list[ForecastModelView]
    feedings: list[FeedingView]
    harvests: list[HarvestView]
