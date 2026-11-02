from aerona.api.schemas.common import ApiModel, ErrorCode
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState, LinkGroup
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory, ThreadStatus
from aerona.domain.enums.creator import CreatorMoodLabel, CreatorPassion
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.intervention import Disaster, InterventionKind, Miracle
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.domain.enums.node import ActorKind, NodeKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.enums.travel import JourneyStatus, TravelMethod
from aerona.domain.enums.world import ClimateEra, Discovery, FateMode, LoreLanguage, SkyEventKind, SonDistribution, StarType, WorldType
from aerona.events.kinds import EventKind
from aerona.services.player.catalog import ActionGroup, ActionMode


class EnumCatalogue(ApiModel):
    event_kinds: list[EventKind]
    job_statuses: list[JobStatus]
    job_kinds: list[JobKind]
    rarities: list[Rarity]
    entity_types: list[EntityType]
    entity_statuses: list[EntityStatus]
    entity_flags: list[EntityFlag]
    chronicle_kinds: list[ChronicleKind]
    action_kinds: list[ActionKind]
    action_groups: list[ActionGroup]
    action_modes: list[ActionMode]
    node_kinds: list[NodeKind]
    actor_kinds: list[ActorKind]
    bond_kinds: list[BondKind]
    bond_states: list[BondState]
    notification_categories: list[NotificationCategory]
    thread_statuses: list[ThreadStatus]
    son_statuses: list[SonStatus]
    stats: list[Stat]
    domains: list[Domain]
    world_types: list[WorldType]
    star_types: list[StarType]
    discoveries: list[Discovery]
    climate_eras: list[ClimateEra]
    sky_events: list[SkyEventKind]
    travel_methods: list[TravelMethod]
    journey_statuses: list[JourneyStatus]
    foreign_god_statuses: list[ForeignGodStatus]
    interventions: list[InterventionKind]
    miracles: list[Miracle]
    disasters: list[Disaster]
    passions: list[CreatorPassion]
    mood_labels: list[CreatorMoodLabel]
    fate_modes: list[FateMode]
    son_distributions: list[SonDistribution]
    lore_languages: list[LoreLanguage]
    error_codes: list[ErrorCode]


class Labelled(ApiModel):
    key: str
    label: str


class EntityTypeInfo(Labelled):
    plural: str
    containers: list[EntityType]
    location_required: bool
    stats: list[str]


class BondKindInfo(Labelled):
    category: str
    fate_suggestable: bool
    weavable: bool
    link_groups: list[LinkGroup]


class LinkGroupInfo(Labelled):
    kinds: list[str]


class WorldTypeInfo(Labelled):
    description: str
    domains: list[Domain]
    living: bool
    realm_of_dead: bool


class NotificationCategoryInfo(Labelled):
    severity: int
    enabled_by_default: bool


class Catalogue(ApiModel):
    enums: EnumCatalogue
    rarities: list[Labelled]
    entity_types: list[EntityTypeInfo]
    bond_kinds: list[BondKindInfo]
    link_groups: list[LinkGroupInfo]
    domains: list[Labelled]
    world_types: list[WorldTypeInfo]
    chronicle_kinds: list[Labelled]
    notification_categories: list[NotificationCategoryInfo]
    climates: list[Labelled]
    creature_traits: list[Labelled]
    passions: list[Labelled]
