from pydantic import BaseModel, Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.api.schemas.records import BondView, ChronicleLineRecord, EntityRecord, EntitySummary, ImageRecord, NodeRef
from aerona.constants.api import ENTITY_PAGE_DEFAULT, ENTITY_PAGE_MAX
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.services.importance import ArchiveMode


class SimilarRecord(ApiModel):
    entity: EntitySummary
    score: float
    reasons: list[str]


class FactView(ApiModel):
    id: int
    subject: NodeRef | None
    predicate: str
    object: NodeRef | None
    object_text: str | None
    epoch: int


class Perspective(ApiModel):
    id: int
    epoch: int
    people_id: int
    people_name: str | None
    historian: str | None
    text: str


class Importance(ApiModel):
    importance: int
    archived: bool
    reason: str | None
    last_mention: int


class SocietyInsight(ApiModel):
    shares: dict[str, float]
    satisfaction: dict[str, int]
    stocks: dict[str, int]
    prices: dict[str, int]
    unhappiest: str | None
    bankruptcy_risk: bool
    uprising_risk: bool


class LifeInsight(ApiModel):
    age: int | None
    lifespan: int
    lifespan_base: int
    medicine_bonus: int
    notable_bonus: int
    immortal: bool
    death_year: int | None
    kill_chance_pct: int
    son_kill_cost: int
    creator_kill_cost: int


class CapacityInsight(ApiModel):
    capacity: int
    region_population: int
    occupancy_pct: int
    region: NodeRef | None


class ExplorationInsight(ApiModel):
    regions: int
    places: int
    communities: int
    pressure: float
    narrow: bool


class KnowledgeInsight(ApiModel):
    branch: str | None
    level: int
    level_cap: int
    branch_multiplier: float


class ResourceInsight(ApiModel):
    mechanics: list[str]
    weighed: bool
    depleting: bool
    depleted: bool


class FaithInsight(ApiModel):
    revered: list[NodeRef]
    syncretic: bool


class RewardInsight(ApiModel):
    son: NodeRef | None
    xp: int
    renown: int
    essence: int
    cost: int
    land: bool
    fade_pct: int
    repeats: int
    taken_back_pct: int
    thread_reverted: bool


class EntityInsight(ApiModel):
    society: SocietyInsight | None = None
    life: LifeInsight | None = None
    capacity: CapacityInsight | None = None
    exploration: ExplorationInsight | None = None
    knowledge: KnowledgeInsight | None = None
    resource: ResourceInsight | None = None
    faith: FaithInsight | None = None
    reward: RewardInsight | None = None
    ancestors: list[NodeRef] = Field(default_factory=list)
    descendants: list[NodeRef] = Field(default_factory=list)


class EntityDetail(ApiModel):
    entity: EntityRecord
    cover: str | None
    creator_son: NodeRef | None
    maker: NodeRef | None
    patron: NodeRef | None
    breadcrumb: list[NodeRef]
    contents: list[EntitySummary]
    content_total: int
    flags: list[EntityFlag]
    traits: list[CreatureTrait]
    tags: list[str]
    bonds: list[BondView]
    bond_total: int
    chronicle: list[ChronicleLineRecord]
    chronicle_total: int
    facts: list[FactView]
    perspectives: list[Perspective]
    similar: list[SimilarRecord]
    anchored_sons: list[NodeRef]
    importance: Importance | None
    images: list[ImageRecord]
    insight: EntityInsight


class ArchiveRequest(RequestModel):
    mode: ArchiveMode


class MapPositionRequest(RequestModel):
    x: float
    y: float


class EntityQuery(BaseModel):
    entity_type: EntityType | None = Field(default=None, alias="type")
    q: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=20)
    world_id: int | None = Field(default=None, ge=1)
    hide_archived: bool = False
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=ENTITY_PAGE_DEFAULT, ge=1, le=ENTITY_PAGE_MAX)
