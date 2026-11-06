from datetime import datetime

from pydantic import Field, computed_field

from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent, PrayerRequest
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory, ThreadStatus
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import ArchiveOverride, EntityOrigin, EntityStatus, EntityType, LegendCategory, MortalRole
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.meta import ImageMime, ImageOrigin
from aerona.domain.enums.node import ActorKind, NodeKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import ExistenceBand, PowerEffect, ReputationLabel, SonDeathCause, SonStatus, Stat
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, RouteClosure, RouteState, TravelMethod
from aerona.domain.enums.war import DebtStatus
from aerona.domain.enums.world import Atmosphere, ClimateEra, Discovery, FateMode, Gravity, LoreLanguage, SonDistribution, StarType, WorldType
from aerona.domain.models.entity_stats import EntityStats
from aerona.domain.models.phonology import Phonology
from aerona.domain.models.profiles import EntityDepth, Epic, ExistenceProfile, GodDepth, Personality, TravelResource
from aerona.domain.models.records import ChronicleAuditReport, CouncilMinutes, EpochStatsData, JourneyEvent


class NodeRef(ApiModel):
    id: int
    kind: NodeKind
    name: str


class GodStats(ApiModel):
    strength: int
    endurance: int
    agility: int
    wisdom: int
    cunning: int
    will: int
    creativity: int
    charisma: int
    might: int


class SonPower(ApiModel):
    slot: int
    name: str
    description: str
    effect: PowerEffect
    param_entity_type: EntityType | None
    param_stat: Stat | None


class SonRecord(ApiModel):
    id: int
    name: str
    title: str
    rarity: Rarity
    stars: int
    domain_primary: Domain
    domain_secondary: Domain
    strength: int
    endurance: int
    agility: int
    wisdom: int
    cunning: int
    will: int
    creativity: int
    charisma: int
    might: int
    sanity: int | None
    loyalty: int
    ambition: int
    wrath: int
    mercy: int
    personality: Personality
    existence_profile: ExistenceProfile | None
    existence: int
    fading_epochs: int
    hp: int
    essence: int
    faith: int
    fame: int
    xp: int
    level: int
    status: SonStatus
    sleep_epochs_left: int
    chained: bool
    rebel: bool
    outer_bargain_forbidden: bool
    standing_order: str | None
    order_absolute: bool
    turn_rank: int | None
    plan: str | None
    plan_epoch: int | None = None
    epic: Epic | None
    anchor_entity_id: int | None
    corpse_entity_id: int | None
    parent_son_id: int | None
    co_parent_son_id: int | None
    current_world_id: int | None
    manually_assigned_epoch: int | None
    birth_epoch: int
    death_epoch: int | None
    death_cause: SonDeathCause | None
    last_acted_epoch: int
    reputation_love: int | None
    reputation_fear: int | None
    reputation_forgotten: int | None
    reputation_unanswered: int | None
    reputation_last_contact_epoch: int | None
    reputation_label: ReputationLabel | None
    manual_love: int
    manual_fear: int
    manual_forgotten: int
    image_prompt: str | None


class Requirement(ApiModel):
    stars: int
    level: int
    fame: int
    essence: int


class Ascension(Requirement):
    target: Rarity


class Kin(ApiModel):
    id: int
    name: str
    value: int


class SonCard(ApiModel):
    last_action: str | None
    last_action_epoch: int | None
    last_words: str | None
    reputation: str | None
    best_friend: Kin | None
    worst_rival: Kin | None


class SonPublic(ApiModel):
    son: SonRecord
    powers: list[SonPower]
    max_hp: int
    max_essence: int
    action_points: int
    power_cap: int
    band: ExistenceBand
    band_label: str
    band_effect: str
    band_action_loss: int
    unlocked_powers: int
    next_star: Requirement | None
    ascension: Ascension | None
    cover: str | None
    card: SonCard


class EntitySummary(ApiModel):
    id: int
    name: str
    title: str | None
    entity_type: EntityType
    subtype: str | None
    status: EntityStatus
    world_id: int
    location_id: int | None
    power_level: int
    birth_epoch: int
    end_epoch: int | None
    importance: int | None
    favorite: bool
    pending_name: bool


class EntityRecord(EntitySummary):
    description: str
    stats: EntityStats
    domain: Domain | None
    origin: EntityOrigin
    creator_son_id: int | None
    maker_entity_id: int | None
    mortal_role: MortalRole | None
    legend_category: LegendCategory | None
    fate_note: str | None
    depth: EntityDepth | None
    archive_override: ArchiveOverride | None
    private_note: str | None
    map_x: float | None
    map_y: float | None
    image_prompt: str | None
    civ_tier: int | None
    sanity: int | None
    last_acted_epoch: int
    is_underworld: bool
    is_water: bool


class CosmosRecord(ApiModel):
    id: int
    name: str
    lore_language: LoreLanguage
    seed_idea: str
    cosmology: str
    tone: str
    epoch: int
    epoch_start_year: int
    doom_clock: int
    fate_mode: FateMode
    son_distribution: SonDistribution
    council_every_epochs: int | None
    mortal_agents_per_epoch: int | None
    mortal_agent_parallelism: int | None
    fate_debt_epoch: int | None
    alignment_until_epoch: int | None
    map_version: int
    primary_world_id: int | None
    travel_resource: TravelResource | None
    created_at: datetime


class CreatorRecord(ApiModel):
    id: int
    name: str
    title: str | None
    appearance: str | None
    temperament: str | None
    image_prompt: str | None
    note: str | None
    essence: int
    mood_contentment: int
    mood_anger: int
    mood_interest: int
    mood_loneliness: int
    passions: list[str]
    passions_automatic: bool
    depth: GodDepth | None
    epic: Epic | None


class WorldRecord(ApiModel):
    id: int
    name: str
    world_type: WorldType
    star_id: int | None
    parent_world_id: int | None
    orbit: float
    gravity: Gravity
    atmosphere: Atmosphere
    time_factor: float
    discovery: Discovery
    danger: int
    leakage: int
    cosmology: str | None
    phonology: Phonology | None
    description: str | None
    image_prompt: str | None
    creator_son_id: int | None
    patron_son_id: int | None
    patron_automatic: bool
    epoch_star_entity_id: int | None
    mirror_twin_id: int | None
    mortal_agents: int | None
    climate_era: ClimateEra | None
    climate_epochs_left: int | None
    climate_since_epoch: int | None
    created_epoch: int
    terrain_seed: str
    terrain_sea: float
    terrain_mountains: float
    terrain_humidity: float


class StarRecord(ApiModel):
    id: int
    name: str
    star_type: StarType
    brightness: int
    x: float
    y: float
    description: str | None
    image_prompt: str | None
    created_epoch: int
    cover: str | None = None


class ForeignGodPower(ApiModel):
    slot: int
    name: str
    effect: str
    description: str


class ForeignGodRecord(ApiModel):
    id: int
    name: str
    title: str | None
    domain_primary: Domain
    domain_secondary: Domain | None
    world_id: int
    power: int
    faith: int
    stance: int
    status: ForeignGodStatus
    contacted: bool
    description: str | None
    image_prompt: str | None
    strength: int
    endurance: int
    agility: int
    wisdom: int
    cunning: int
    will: int
    creativity: int
    charisma: int
    might: int
    sanity: int | None
    personality: Personality | None
    existence_profile: ExistenceProfile | None
    depth: GodDepth | None
    awakening_pressure: int
    awakening_average: float | None
    created_epoch: int
    defeated_epoch: int | None
    death_epoch: int | None
    cover: str | None = None


class BondRecord(ApiModel):
    id: int
    source_node_id: int
    target_node_id: int
    kind: BondKind
    description: str | None
    role: BondRole | None
    epoch: int
    state: BondState
    closed_epoch: int | None
    closed_reason: str | None
    war_id: int | None
    debt_amount: int | None
    debt_what: str | None
    debt_due_epoch: int | None
    debt_status: DebtStatus | None


class BondView(BondRecord):
    outgoing: bool
    other: NodeRef | None
    derived: bool | None = None


class RouteStatusRecord(ApiModel):
    open: bool
    state: RouteState
    reason: str
    opens_epoch: int | None
    closes_epoch: int | None


class RouteRecord(ApiModel):
    id: int
    world_a_id: int
    world_b_id: int
    method: TravelMethod
    duration_epochs: int
    danger: int
    known: bool
    controller_entity_id: int | None
    vehicle_entity_id: int | None
    builder_son_id: int | None
    bound_star_id: int | None
    description: str | None
    created_epoch: int
    active: bool
    closure: RouteClosure | None
    temp_open_until_epoch: int | None
    temp_closed_until_epoch: int | None
    status: RouteStatusRecord


class JourneyRecord(ApiModel):
    id: int
    traveller_entity_id: int
    route_id: int
    vehicle_entity_id: int | None
    origin_world_id: int
    destination_world_id: int
    intent: JourneyIntent
    population: int
    epochs_left: int
    status: JourneyStatus
    events: list[JourneyEvent]
    memory_lost: bool
    start_epoch: int
    end_epoch: int | None
    result_entity_id: int | None


class ChronicleLineRecord(ApiModel):
    id: int
    epoch: int
    year: int | None
    kind: ChronicleKind
    son_id: int | None
    world_id: int | None
    text: str
    template_key: str | None
    created_at: datetime
    entity_ids: list[int] = Field(default_factory=list)


class ThreadRecord(ApiModel):
    id: int
    epoch: int
    text: str
    status: ThreadStatus
    closing_text: str | None
    closed_epoch: int | None
    progress: int
    related: list[NodeRef] = Field(default_factory=list)


class MessageRecord(ApiModel):
    id: int
    epoch: int
    sender_node_id: int
    recipient_node_id: int
    intent: MessageIntent
    text: str
    request: PrayerRequest | None
    wish: str | None
    is_read: bool
    answered: bool
    answered_epoch: int | None
    answer_essence: int | None
    created_at: datetime


class CouncilRecord(ApiModel):
    id: int
    epoch: int
    topic: str
    minutes: CouncilMinutes
    passed: bool
    created_at: datetime


class EpochRecord(ApiModel):
    epoch: int
    name: str | None
    narrative: str | None
    summary: str | None
    year_start: int | None
    year_end: int | None
    closed_at: datetime | None
    chronicler_name: str | None
    chronicler_identity: str | None
    audit: ChronicleAuditReport | None = None


class NotificationRecord(ApiModel):
    id: int
    epoch: int | None
    category: NotificationCategory
    severity: int
    title: str
    body: str | None
    target_node_id: int | None
    chronicle_id: int | None
    is_read: bool
    created_at: datetime
    job_id: str | None = None
    entity_ids: list[int] = Field(default_factory=list)


class ImageRecord(ApiModel):
    id: int
    target_node_id: int
    file_name: str
    mime: ImageMime
    sha256: str
    origin: ImageOrigin
    caption: str | None
    prompt: str | None
    style: str | None
    is_cover: bool
    size_bytes: int
    width: int | None
    height: int | None
    created_at: datetime

    @computed_field
    def content_type(self) -> str:
        return self.mime.value


class MapNoteRecord(ApiModel):
    id: int
    world_id: int
    x: float
    y: float
    text: str
    color: str | None
    created_at: datetime


class ActionRecord(ApiModel):
    id: int
    epoch: int
    actor_kind: ActorKind
    actor_node_id: int | None
    kind: ActionKind
    target_node_id: int | None
    essence_spent: int
    summary: str | None
    created_at: datetime


class EpochStatsRecord(ApiModel):
    epoch: int
    live: bool
    data: EpochStatsData


class EntityNoteRecord(ApiModel):
    entity_id: int
    entity_name: str
    entity_type: EntityType
    world_id: int
    text: str


class NotesView(ApiModel):
    entity_notes: list[EntityNoteRecord]
    map_notes: list[MapNoteRecord]
