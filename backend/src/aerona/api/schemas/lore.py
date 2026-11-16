from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import (
    ArtMedium,
    BacklashKind,
    BoostTrigger,
    CalendarSlot,
    Capability,
    CurseKind,
    CustomCatalog,
    IdeologyTenet,
    ItemClass,
    ItemDeed,
    LanguageRegister,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    ProphecyConsequence,
    ProphecyPredicate,
    ProphecyState,
    ResearchChooser,
    RiteEffectKind,
    RumourChannel,
    SpeakerKind,
    SummonForm,
    Technique,
    TraditionEffectKind,
    TraditionKind,
)
from aerona.domain.enums.discovery import (
    AgeKind,
    AnomalyKind,
    ArtDiscipline,
    BlueprintKind,
    BlueprintSource,
    EraDeed,
    GreatField,
    ResearchIncident,
    TheoryDomain,
)
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import KnowledgeBranch


class SpeakerView(ApiModel):
    community: NodeRef | None
    kind: SpeakerKind
    share: int
    since_epoch: int
    held: bool = False


class KinView(ApiModel):
    language: NodeRef | None
    value: int
    held: bool = False


class RegisterView(ApiModel):
    holder: NodeRef | None
    kind: LanguageRegister
    language: NodeRef | None
    since_epoch: int
    held: bool


class IncidentRef(ApiModel):
    id: int
    kind: str
    epoch: int
    note: str | None


class LanguageCard(ApiModel):
    prestige: int
    prestige_parts: dict[str, int]
    standardisation: int
    liturgical: bool
    lingua_franca: bool
    speakers: list[SpeakerView]
    kin: list[KinView]
    registers: list[RegisterView]
    locked: list[str]


class LegendCard(ApiModel):
    archetype: LegendArchetype
    credence: int
    distortion: int
    subject: NodeRef | None
    moral: dict[str, int]
    tellers: list[NodeRef]
    bards: list[NodeRef]
    fixed_in: NodeRef | None
    source: IncidentRef | None = None
    custom_archetype_id: int | None = None
    locked: list[str]


class KeeperView(ApiModel):
    community: NodeRef | None
    participation: int
    skipped: int
    last_celebrated_epoch: int | None
    held: bool = False


class TraditionEffectView(ApiModel):
    effect: TraditionEffectKind
    target: str
    magnitude: int


class TraditionCard(ApiModel):
    kind: TraditionKind
    calendar_slot: CalendarSlot | None
    season_position: int | None = None
    calendar_entity_id: int | None = None
    notable_year_id: int | None = None
    in_season: bool | None = None
    cost: dict[str, int]
    effects: list[TraditionEffectView]
    taboo_target: str | None
    taboo_act: ActKind | None = None
    custom_kind_id: int | None = None
    origin: NodeRef | None
    origin_incident: IncidentRef | None = None
    keepers: list[KeeperView]
    locked: list[str]


class AdherentView(ApiModel):
    community: NodeRef | None
    strength: int
    state: bool
    since_epoch: int


class IdeologyCard(ApiModel):
    founder: NodeRef | None
    tenets: list[IdeologyTenet]
    appeal: dict[str, int]
    values: dict[str, int]
    adherents: list[AdherentView]
    locked: list[str]
    texts: list[NodeRef]
    custom_tenets: list[int]


class TheoryAdherentView(ApiModel):
    holder: NodeRef
    strength: int
    orthodox: bool
    since_epoch: int
    locked: list[str]


class AnomalyView(ApiModel):
    id: int
    kind: AnomalyKind
    label: str
    weight: int
    epoch: int
    witness: NodeRef | None


class ShiftView(ApiModel):
    id: int
    community: NodeRef | None
    old: NodeRef | None
    new: NodeRef | None
    epoch: int


class TheoryCard(ApiModel):
    domain: TheoryDomain
    subject: str
    claim: str
    correctness: int
    explanatory_power: int
    pressure: int
    founder: NodeRef | None
    founding_book: NodeRef | None
    rival: NodeRef | None
    endorsed_by: list[NodeRef]
    condemned_by: list[NodeRef]
    revealed_by_son_id: int | None
    adherents: list[TheoryAdherentView]
    anomalies: list[AnomalyView]
    shifts: list[ShiftView]
    locked: list[str]


class PractitionerView(ApiModel):
    holder: NodeRef
    mastery: int
    since_epoch: int
    locked: list[str]


class ArtFormCard(ApiModel):
    discipline: ArtDiscipline
    discipline_label: str
    structure: dict[str, str | int]
    parts: list[str]
    origin: NodeRef | None
    founder: NodeRef | None
    language: NodeRef | None
    difficulty: int
    prestige: int
    sacred: bool
    notation: bool
    occasions: list[str]
    parents: list[NodeRef]
    children: list[NodeRef]
    practitioners: list[PractitionerView]
    artworks: list[NodeRef]
    banned_in: list[NodeRef]
    locked: list[str]


class NameView(ApiModel):
    node_id: int
    name: str
    language: NodeRef | None
    gloss: str
    morphemes: list[str]
    epoch: int
    locked: list[str]


class ExonymView(ApiModel):
    language: NodeRef
    form: str
    gloss: str
    epoch: int
    locked: list[str]


class EpithetView(ApiModel):
    epithet: str
    gloss: str
    deed: str
    language: NodeRef | None
    epoch: int
    locked: list[str]


class NameCard(ApiModel):
    node_id: int
    current_name: str
    epithets_allowed: bool
    meaning: NameView | None
    exonyms: list[ExonymView]
    epithet: EpithetView | None


class RiteEffectView(ApiModel):
    effect: RiteEffectKind
    magnitude: int
    detail: str | None
    damage_type: DamageType | None = None
    summon_form: SummonForm | None = None
    custom_kind_id: int | None = None


class CastingView(ApiModel):
    id: int
    caster: NodeRef | None
    target: NodeRef | None
    epoch: int
    succeeded: bool
    backlash: BacklashKind | None
    effect: str


class RiteCard(ApiModel):
    school: MagicSchool
    source: MagicSource
    requirements: dict[str, int | str]
    cost: dict[str, int]
    power: int
    backlash_chance: int
    backlash: BacklashKind
    holy: bool
    heretical: bool
    inventor: NodeRef | None
    effects: list[RiteEffectView]
    castings: list[CastingView]
    locked: list[str]
    forbidden_by: list[NodeRef]


class ProphecyCard(ApiModel):
    predicate: ProphecyPredicate
    args: dict[str, int | str]
    deadline_epoch: int | None
    seer: NodeRef | None
    audience: list[NodeRef]
    pressure: int
    state: ProphecyState
    resolved_epoch: int | None
    locked: list[str]
    consequence_kind: ProphecyConsequence | None = None
    consequence: NodeRef | None = None
    retold: int = 0
    forged: bool = False
    rival: NodeRef | None = None


class BookPage(ApiModel):
    knowledge: NodeRef | None
    fidelity: int


class CustomTechniqueView(ApiModel):
    kind_id: int
    name: str
    base: Technique
    secret: bool


class DeedView(ApiModel):
    epoch: int
    deed: ItemDeed
    actor: NodeRef | None
    note: str
    id: int = 0


class EnchantmentView(ApiModel):
    effect: RiteEffectKind
    strength: int
    rite: NodeRef | None
    since_epoch: int


class ItemCard(ApiModel):
    item_class: ItemClass
    material: str | None
    quality: int
    condition: int
    damage_type: str | None
    reach: int
    coverage: int
    weight: int
    curse: CurseKind
    value: int
    renown: int
    maker: NodeRef | None
    owner: NodeRef | None
    regalia_of: NodeRef | None
    symbol: bool
    history: list[DeedView]
    enchantments: list[EnchantmentView]
    contents: list[NodeRef]
    locked: list[str]
    secondary_materials: list[str]
    bound_spirit: NodeRef | None = None
    prosthesis_for: str | None = None
    custom_class_id: int | None = None
    book_contents: list[BookPage]


class ArtworkCard(ApiModel):
    medium: ArtMedium
    performed: bool
    author: NodeRef | None
    patron: NodeRef | None
    subject: NodeRef | None
    message: dict[str, int]
    quality: int
    copies: int
    language: NodeRef | None
    translations: list[NodeRef]
    propaganda: bool
    locked: list[str]
    canon: bool = False


class LoreCard(ApiModel):
    entity_id: int
    language: LanguageCard | None = None
    legend: LegendCard | None = None
    tradition: TraditionCard | None = None
    ideology: IdeologyCard | None = None
    rite: RiteCard | None = None
    prophecy: ProphecyCard | None = None
    item: ItemCard | None = None
    artwork: ArtworkCard | None = None
    theory: TheoryCard | None = None
    art_form: ArtFormCard | None = None


class LevelView(ApiModel):
    branch: KnowledgeBranch
    level: int
    practitioners: int
    progress: int
    secret: bool
    open: bool
    locked: list[str]
    frontier: int = 0


class TechniqueView(ApiModel):
    technique: Technique
    branch: KnowledgeBranch
    level: int
    label: str
    effect: str
    known: bool
    secret: bool
    reachable: bool
    institution: bool
    progress: int


class FocusView(ApiModel):
    technique: Technique
    chooser: ResearchChooser
    options: list[Technique]
    epoch: int
    locked: list[str]


class InstitutionView(ApiModel):
    technique: Technique
    origin: bool
    embraced: bool
    since_epoch: int
    refused_epochs: int
    locked: list[str]


class BoostView(ApiModel):
    id: int
    technique: Technique
    trigger: BoostTrigger
    progress: int
    epoch: int


class GreatPointsView(ApiModel):
    field: GreatField
    label: str
    points: int
    threshold: int
    locked: list[str]


class GreatPersonView(ApiModel):
    mortal: NodeRef
    field: GreatField
    label: str
    deed: str
    promoted_epoch: int
    deed_done: bool
    deed_epoch: int | None
    locked: list[str]


class IncidentView(ApiModel):
    id: int
    kind: ResearchIncident
    label: str
    technique: Technique | None
    branch: KnowledgeBranch | None
    severity: int
    dead: int
    epoch: int


class StudyView(ApiModel):
    item: NodeRef
    technique: Technique
    progress: int
    epoch: int
    locked: list[str]


class BlueprintView(ApiModel):
    id: int
    name: str
    kind: BlueprintKind
    kind_label: str
    subject: str
    source: BlueprintSource
    source_label: str
    quality: int
    licensed_to: list[NodeRef]
    since_epoch: int
    locked: list[str]


class EraDeedView(ApiModel):
    id: int
    deed: EraDeed
    label: str
    points: int
    epoch: int
    subject: NodeRef | None


class BannedWorkView(ApiModel):
    work: NodeRef
    since_epoch: int
    locked: list[str]


class RealmEraView(ApiModel):
    polity_id: int
    score: int
    age: AgeKind
    since_epoch: int
    lowest: int
    golden_at: int
    dark_at: int
    locked: list[str]
    deeds: list[EraDeedView]
    banned: list[BannedWorkView]


class WorldEraView(ApiModel):
    world_id: int
    era: int
    name: str
    top: int
    since_epoch: int
    next_share: int
    locked: list[str]


class CapabilityView(ApiModel):
    capability: Capability
    label: str
    effect: str
    held: bool


class LearningCard(ApiModel):
    holder_id: int
    levels: list[LevelView]
    techniques: list[TechniqueView]
    books: list[NodeRef]
    custom_techniques: list[CustomTechniqueView]
    focus: FocusView | None
    institutions: list[InstitutionView]
    boosts: list[BoostView]
    capabilities: list[CapabilityView]
    great_points: list[GreatPointsView]
    great_people: list[GreatPersonView]
    incidents: list[IncidentView]
    studies: list[StudyView]
    designs: list[BlueprintView]


class GateNeed(ApiModel):
    branch: KnowledgeBranch
    level: int


class BranchSpec(ApiModel):
    branch: KnowledgeBranch
    all_of: list[GateNeed]
    any_of: list[GateNeed]


class TechniqueSpecView(ApiModel):
    technique: Technique
    branch: KnowledgeBranch
    level: int
    label: str
    effect: str
    all_of: list[GateNeed]
    any_of: list[GateNeed]
    institution: bool


class TriggerSpecView(ApiModel):
    trigger: BoostTrigger
    label: str
    techniques: list[Technique]


class CapabilitySpecView(ApiModel):
    capability: Capability
    label: str
    effect: str
    branches: list[GateNeed]
    all_of: list[Technique]
    any_of: list[Technique]


class TechGraph(ApiModel):
    branches: list[BranchSpec]
    techniques: list[TechniqueSpecView]
    triggers: list[TriggerSpecView]
    capabilities: list[CapabilitySpecView]


class TongueRank(ApiModel):
    language: NodeRef
    prestige: int
    lingua_franca: bool
    liturgical: bool
    speakers: int


class TongueAtlas(ApiModel):
    ranking: list[TongueRank]
    matrix: list[list[int]]
    registers: list[RegisterView]


class CustomKindView(ApiModel):
    id: int
    catalog: CustomCatalog
    base: str
    name: str
    description: str
    params: dict[str, int | str | list[str] | dict[str, int]]
    world_id: int | None
    created_epoch: int


class CustomKinds(ApiModel):
    kinds: list[CustomKindView]


class RumourView(ApiModel):
    id: int
    incident_id: int
    text: str
    kind: str
    happened_epoch: int
    fidelity: int
    channel: RumourChannel
    hops: int
    heard_epoch: int
    lingered: int
    source: NodeRef | None
    legend: NodeRef | None
    planted: bool
    atrocity: bool
    alarm: bool
    carriers: int
    locked: list[str]


class RumourBoard(ApiModel):
    community_id: int
    rumours: list[RumourView]
