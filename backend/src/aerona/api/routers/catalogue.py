from fastapi import APIRouter

from aerona.api.schemas.catalogue import (
    BondKindInfo,
    Catalogue,
    EntityTypeInfo,
    EnumCatalogue,
    Labelled,
    LinkGroupInfo,
    WorldTypeInfo,
)
from aerona.catalog.bonds import BOND_KINDS, LINK_GROUP_LABELS, link_groups_of, ordered_link_groups
from aerona.catalog.chronicle import CHRONICLE_KINDS
from aerona.catalog.creator import CREATOR_PASSIONS
from aerona.catalog.creatures import CREATURE_TRAITS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.job import JobStatus
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind

router = APIRouter(tags=["catalogue"])


def enum_catalogue() -> EnumCatalogue:
    return EnumCatalogue(
        event_kinds=list(EventKind),
        job_statuses=list(JobStatus),
        actor_kinds=list(ActorKind),
        miracles=list(Miracle),
        disasters=list(Disaster),
    )


@router.get("/catalogue/enums", response_model=EnumCatalogue)
async def read_enums() -> EnumCatalogue:
    return enum_catalogue()


@router.get("/catalogue", response_model=Catalogue)
async def read_catalogue() -> Catalogue:
    return Catalogue(
        enums=enum_catalogue(),
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
        creature_traits=[Labelled(key=trait.value, label=spec.label) for trait, spec in CREATURE_TRAITS.items()],
        passions=[Labelled(key=passion.value, label=spec.label) for passion, spec in CREATOR_PASSIONS.items()],
    )
