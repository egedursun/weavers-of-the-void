from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import (
    ArtMedium,
    BacklashKind,
    CurseKind,
    IdeologyTenet,
    ItemClass,
    ItemDeed,
    LegendArchetype,
    MagicSchool,
    MagicSource,
    ProphecyPredicate,
    ProphecyState,
    RiteEffectKind,
    SpeakerKind,
    Technique,
    TraditionKind,
)
from aerona.domain.enums.society import KnowledgeBranch


class SpeakerView(ApiModel):
    community: NodeRef | None
    kind: SpeakerKind
    share: int
    since_epoch: int


class KinView(ApiModel):
    language: NodeRef | None
    value: int


class LanguageCard(ApiModel):
    prestige: int
    prestige_parts: dict[str, int]
    standardisation: int
    liturgical: bool
    lingua_franca: bool
    speakers: list[SpeakerView]
    kin: list[KinView]
    locked: list[str]


class LegendCard(ApiModel):
    archetype: LegendArchetype
    credence: int
    distortion: int
    subject: NodeRef | None
    moral: dict[str, int]
    tellers: list[NodeRef]
    fixed_in: NodeRef | None
    locked: list[str]


class KeeperView(ApiModel):
    community: NodeRef | None
    participation: int
    skipped: int
    last_celebrated_epoch: int | None


class TraditionCard(ApiModel):
    kind: TraditionKind
    calendar_slot: str | None
    season_position: int | None = None
    calendar_entity_id: int | None = None
    notable_year_id: int | None = None
    in_season: bool | None = None
    cost: dict[str, int]
    effects: dict[str, int]
    taboo_target: str | None
    origin: NodeRef | None
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


class RiteEffectView(ApiModel):
    effect: RiteEffectKind
    magnitude: int
    detail: str | None


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


class DeedView(ApiModel):
    epoch: int
    deed: ItemDeed
    actor: NodeRef | None
    note: str


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


class LevelView(ApiModel):
    branch: KnowledgeBranch
    level: int
    practitioners: int
    progress: int
    secret: bool
    open: bool
    locked: list[str]


class TechniqueView(ApiModel):
    technique: Technique
    branch: KnowledgeBranch
    level: int
    label: str
    effect: str
    known: bool
    secret: bool
    reachable: bool


class LearningCard(ApiModel):
    holder_id: int
    levels: list[LevelView]
    techniques: list[TechniqueView]
    books: list[NodeRef]


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


class TechGraph(ApiModel):
    branches: list[BranchSpec]
    techniques: list[TechniqueSpecView]


class TongueRank(ApiModel):
    language: NodeRef
    prestige: int
    lingua_franca: bool
    liturgical: bool
    speakers: int


class TongueAtlas(ApiModel):
    ranking: list[TongueRank]
    matrix: list[list[int]]
