from fastapi import APIRouter

from aerona.api.schemas.catalogue import (
    BondKindInfo,
    Catalogue,
    EntityTypeInfo,
    EnumCatalogue,
    Labelled,
    LinkGroupInfo,
    NotificationCategoryInfo,
    WorldTypeInfo,
)
from aerona.api.schemas.common import ErrorCode
from aerona.catalog.bonds import BOND_KINDS, LINK_GROUP_LABELS, link_groups_of, ordered_link_groups
from aerona.catalog.chronicle import CHRONICLE_KINDS, NOTIFICATION_CATEGORIES
from aerona.catalog.climate import CLIMATES
from aerona.catalog.creator import CREATOR_PASSIONS
from aerona.catalog.creatures import CREATURE_TRAITS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
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

router = APIRouter(tags=["catalogue"])


def enum_catalogue() -> EnumCatalogue:
    return EnumCatalogue(
        event_kinds=list(EventKind),
        job_statuses=list(JobStatus),
        job_kinds=list(JobKind),
        rarities=list(Rarity),
        entity_types=list(EntityType),
        entity_statuses=list(EntityStatus),
        entity_flags=list(EntityFlag),
        chronicle_kinds=list(ChronicleKind),
        action_kinds=list(ActionKind),
        action_groups=list(ActionGroup),
        action_modes=list(ActionMode),
        node_kinds=list(NodeKind),
        actor_kinds=list(ActorKind),
        bond_kinds=list(BondKind),
        bond_states=list(BondState),
        notification_categories=list(NotificationCategory),
        thread_statuses=list(ThreadStatus),
        son_statuses=list(SonStatus),
        stats=list(Stat),
        domains=list(Domain),
        world_types=list(WorldType),
        star_types=list(StarType),
        discoveries=list(Discovery),
        climate_eras=list(ClimateEra),
        sky_events=list(SkyEventKind),
        travel_methods=list(TravelMethod),
        journey_statuses=list(JourneyStatus),
        foreign_god_statuses=list(ForeignGodStatus),
        interventions=list(InterventionKind),
        miracles=list(Miracle),
        disasters=list(Disaster),
        passions=list(CreatorPassion),
        mood_labels=list(CreatorMoodLabel),
        fate_modes=list(FateMode),
        son_distributions=list(SonDistribution),
        lore_languages=list(LoreLanguage),
        error_codes=list(ErrorCode),
    )


@router.get("/catalogue/enums", response_model=EnumCatalogue)
async def read_enums() -> EnumCatalogue:
    return enum_catalogue()


@router.get("/catalogue", response_model=Catalogue)
async def read_catalogue() -> Catalogue:
    return Catalogue(
        enums=enum_catalogue(),
        rarities=[Labelled(key=rarity.value, label=label) for rarity, label in RARITY_LABELS.items()],
        entity_types=[
            EntityTypeInfo(
                key=kind.value,
                label=spec.label,
                plural=spec.plural,
                containers=sorted(spec.containers),
                location_required=spec.location_required,
                stats=[field.key for field in spec.stats],
            )
            for kind, spec in ENTITY_TYPES.items()
        ],
        bond_kinds=[
            BondKindInfo(
                key=kind.value,
                label=spec.label,
                category=spec.category.value,
                fate_suggestable=spec.fate_suggestable,
                weavable=spec.weavable,
                link_groups=link_groups_of(kind.value),
            )
            for kind, spec in BOND_KINDS.items()
        ],
        link_groups=[LinkGroupInfo(key=group.value, label=LINK_GROUP_LABELS[group], kinds=sorted(kinds)) for group, kinds in ordered_link_groups()],
        domains=[Labelled(key=domain.value, label=label) for domain, label in DOMAIN_LABELS.items()],
        world_types=[
            WorldTypeInfo(
                key=kind.value, label=spec.label, description=spec.description, domains=list(spec.domains), living=spec.living, realm_of_dead=spec.realm_of_dead
            )
            for kind, spec in WORLD_TYPES.items()
        ],
        chronicle_kinds=[Labelled(key=kind.value, label=spec.label) for kind, spec in CHRONICLE_KINDS.items()],
        notification_categories=[
            NotificationCategoryInfo(key=category.value, label=spec.label, severity=spec.severity, enabled_by_default=spec.enabled_by_default)
            for category, spec in NOTIFICATION_CATEGORIES.items()
        ],
        climates=[Labelled(key=era.value, label=spec.label) for era, spec in CLIMATES.items()],
        creature_traits=[Labelled(key=trait.value, label=spec.label) for trait, spec in CREATURE_TRAITS.items()],
        passions=[Labelled(key=passion.value, label=spec.label) for passion, spec in CREATOR_PASSIONS.items()],
    )
