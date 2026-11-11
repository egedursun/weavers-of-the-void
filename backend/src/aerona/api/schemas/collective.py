from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.collective import (
    AccountKind,
    AccountMedium,
    AccountStance,
    ArmsInk,
    ArmsRim,
    CascadeOutcome,
    ChargeArrangement,
    CollectiveActKind,
    CollectiveTrigger,
    DatingSystemKind,
    DesignComponentKind,
    DesignKind,
    FormativeKind,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    MobEnd,
    MobStatus,
    MobTarget,
    NormBehaviour,
    NormSituation,
    PartitionLine,
    RoleEligibility,
    RoleKind,
    ShieldShape,
    SocialBias,
    StoryletId,
    StoryletRole,
    StoryletStatus,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.military import HullClass
from aerona.domain.enums.mind import EthicalStance, ValueAxis
from aerona.domain.enums.society import SocialClass


class MoodView(ApiModel):
    anger: int
    anxiety: int
    fervour: int
    deterrence: int
    agitation: int
    last_trigger: CollectiveTrigger | None
    locked: list[str]


class CascadeView(ApiModel):
    id: int
    district_name: str | None
    trigger: CollectiveTrigger
    act: CollectiveActKind
    participants: int
    share: int
    outcome: CascadeOutcome
    deaths: int
    fled: int
    collection_id: int | None
    collection_name: str | None
    epoch: int


class MobView(ApiModel):
    id: int
    act: CollectiveActKind
    size: int
    anger: int
    target: MobTarget
    target_node: NodeRef | None
    leader: NodeRef | None
    status: MobStatus
    ended_by: MobEnd | None
    damage: int
    district_name: str | None
    cascade_id: int | None
    since_epoch: int
    locked: list[str]


class PopularMovementView(ApiModel):
    id: int
    act: CollectiveActKind
    trigger: CollectiveTrigger
    members: int
    strength: int
    leader: NodeRef | None
    cult: NodeRef | None
    faction: NodeRef | None
    since_epoch: int
    ended_epoch: int | None
    locked: list[str]


class AccountStanceView(ApiModel):
    node: NodeRef
    stance: AccountStance


class AccountView(ApiModel):
    id: int
    holder: NodeRef
    author: NodeRef | None
    kind: AccountKind
    medium: AccountMedium
    collection_id: int | None
    collection_name: str | None
    subject: NodeRef | None
    structure: NodeRef | None
    artwork: NodeRef | None
    fidelity: int
    credence: int
    distance: int
    revised_from_id: int | None
    defaced: bool
    epoch: int
    dated: str
    stances: list[AccountStanceView]
    locked: list[str]


class StrikeView(ApiModel):
    node: NodeRef
    by: NodeRef
    active: bool
    since_epoch: int
    locked: list[str]


class MythView(ApiModel):
    holder: NodeRef
    account_id: int | None
    credence: int
    debunked_epoch: int | None
    since_epoch: int
    locked: list[str]


class CommemorationView(ApiModel):
    holder: NodeRef
    collection_id: int
    collection_name: str
    pride: bool
    strength: int
    last_observed_epoch: int | None
    since_epoch: int
    locked: list[str]


class LostLandView(ApiModel):
    claimant: NodeRef
    region: NodeRef
    strength: int
    lost_epoch: int
    claimed_epoch: int | None
    locked: list[str]


class CastView(ApiModel):
    role: StoryletRole
    node: NodeRef


class StoryletChoiceView(ApiModel):
    index: int
    text: str


class StoryletView(ApiModel):
    id: int
    storylet: StoryletId
    title: str
    world_id: int | None
    cast: list[CastView]
    status: StoryletStatus
    chooser: NodeRef | None
    choice: int | None
    step: int
    situation: str
    choices: list[StoryletChoiceView]
    follows_run_id: int | None
    collection_id: int | None
    collection_name: str | None
    due_epoch: int | None
    opened_epoch: int
    resolved_epoch: int | None
    locked: list[str]


class NormView(ApiModel):
    situation: NormSituation
    behaviour: NormBehaviour
    stance: EthicalStance
    since_epoch: int
    locked: list[str]


class NormChangeView(ApiModel):
    id: int
    situation: NormSituation
    behaviour: NormBehaviour
    before: EthicalStance | None
    after: EthicalStance
    cause: str
    epoch: int


class BiasView(ApiModel):
    prestige_pct: int
    conformity_pct: int
    content_pct: int
    locked: list[str]


class CopiedLessonView(ApiModel):
    id: int
    model: NodeRef | None
    bias: SocialBias
    axis: ValueAxis
    shift: int
    epoch: int


class GenerationView(ApiModel):
    generation_epoch: int
    formative: list[FormativeKind]
    value_shifts: dict[ValueAxis, int]
    alive: int
    passed_epoch: int | None
    locked: list[str]


class DiasporaView(ApiModel):
    people: NodeRef
    host: NodeRef
    home: NodeRef | None
    population: int
    ties: int
    remittance: int
    since_epoch: int
    locked: list[str]


class TransitionView(ApiModel):
    fertility_pct: int
    elder_share: int
    urban_share: int
    literacy: int
    locked: list[str]


class SexRatioView(ApiModel):
    males_per_hundred: int
    widows: int
    locked: list[str]


class RoleView(ApiModel):
    role: RoleKind
    eligibility: RoleEligibility
    min_age: int
    classes: list[SocialClass]
    stance: EthicalStance
    since_epoch: int
    locked: list[str]


class DatingView(ApiModel):
    kind: DatingSystemKind
    anchor_year: int
    anchor: NodeRef | None
    label: NodeRef | None
    cycle_years: int
    reformed_epoch: int | None
    since_epoch: int
    today: str
    locked: list[str]


class ArmsLayerView(ApiModel):
    d: str
    ink: ArmsInk
    filled: bool
    width: float
    opacity: float
    evenodd: bool
    clip: str | None
    transform: str | None
    clipped: bool


class ArmsDrawingView(ApiModel):
    view_box: str
    outline: str
    layers: list[ArmsLayerView]


class ArmsDesignQuery(ApiModel):
    shape: ShieldShape = ShieldShape.HEATER
    field: Tincture = Tincture.BLUE
    division: HeraldicDivision = HeraldicDivision.PLAIN
    line: PartitionLine = PartitionLine.STRAIGHT
    second: Tincture | None = None
    charge: HeraldicCharge = HeraldicCharge.NONE
    charge_tincture: Tincture | None = None
    charge_two: HeraldicCharge = HeraldicCharge.NONE
    charge_two_tincture: Tincture | None = None
    charge_three: HeraldicCharge = HeraldicCharge.NONE
    charge_three_tincture: Tincture | None = None
    arrangement: ChargeArrangement = ChargeArrangement.TWO_AND_ONE
    rim: ArmsRim = ArmsRim.LINE
    rim_line: PartitionLine = PartitionLine.STRAIGHT
    rim_tincture: Tincture | None = None
    supporter: HeraldicCharge = HeraldicCharge.NONE
    supporter_pose: SupporterPose = SupporterPose.CROSSED
    supporter_tincture: Tincture | None = None
    crest: HeraldicCharge = HeraldicCharge.NONE
    crest_tincture: Tincture | None = None


class ArmsDesignView(ApiModel):
    shape: ShieldShape
    field: Tincture
    division: HeraldicDivision
    line: PartitionLine
    second: Tincture | None
    charge: HeraldicCharge
    charge_tincture: Tincture | None
    charge_two: HeraldicCharge
    charge_two_tincture: Tincture | None
    charge_three: HeraldicCharge
    charge_three_tincture: Tincture | None
    arrangement: ChargeArrangement
    rim: ArmsRim
    rim_line: PartitionLine
    rim_tincture: Tincture | None
    supporter: HeraldicCharge
    supporter_pose: SupporterPose
    supporter_tincture: Tincture | None
    crest: HeraldicCharge
    crest_tincture: Tincture | None
    blazon: str
    drawing: ArmsDrawingView


class ArmsView(ArmsDesignView):
    holder_kind: HeraldryHolderKind
    motto: str | None
    parent: NodeRef | None
    quartered: NodeRef | None
    since_epoch: int
    locked: list[str]


class ComponentView(ApiModel):
    component: DesignComponentKind
    material_id: int | None
    material_name: str | None
    size: int
    quality: int
    wear: int | None


class MachineDesignView(ApiModel):
    id: int
    owner: NodeRef
    kind: DesignKind
    hull: HullClass | None
    name: str
    designer: NodeRef | None
    parent_design_id: int | None
    mark: int
    mass: int
    speed: int
    range: int
    seaworthiness: int
    cargo: int
    armament: int
    crew: int
    obsolete: bool
    epoch: int
    vessels: int
    components: list[ComponentView]
    locked: list[str]


class MaterialChoice(ApiModel):
    id: int
    name: str


class CollectiveView(ApiModel):
    node: NodeRef
    mood: MoodView | None
    cascades: list[CascadeView]
    mobs: list[MobView]
    movements: list[PopularMovementView]
    accounts: list[AccountView]
    strikes: list[StrikeView]
    myth: MythView | None
    commemorations: list[CommemorationView]
    lost_lands: list[LostLandView]
    storylets: list[StoryletView]
    norms: list[NormView]
    norm_changes: list[NormChangeView]
    biases: BiasView | None
    lessons: list[CopiedLessonView]
    generations: list[GenerationView]
    diasporas: list[DiasporaView]
    transition: TransitionView | None
    sex_ratio: SexRatioView | None
    roles: list[RoleView]
    dating: DatingView | None
    arms: ArmsView | None
    designs: list[MachineDesignView]
    vessel_design_id: int | None
    materials: list[MaterialChoice]


class StoryletStepView(ApiModel):
    text: str
    choices: list[str]


class StoryletSpecView(ApiModel):
    storylet: StoryletId
    title: str
    chooser: StoryletRole
    roles: list[StoryletRole]
    weight: int
    steps: list[StoryletStepView]
