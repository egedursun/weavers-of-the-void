from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.bond import BondCategory, LinkGroup
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.job import JobStatus
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind


class EnumCatalogue(ApiModel):
    event_kinds: list[EventKind]
    job_statuses: list[JobStatus]
    actor_kinds: list[ActorKind]
    miracles: list[Miracle]
    disasters: list[Disaster]


class Labelled(ApiModel):
    key: str
    label: str


class EntityTypeInfo(Labelled):
    plural: str
    containers: list[EntityType]
    location_required: bool
    stats: list[str]


class BondKindInfo(Labelled):
    category: BondCategory
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


class Catalogue(ApiModel):
    enums: EnumCatalogue
    entity_types: list[EntityTypeInfo]
    bond_kinds: list[BondKindInfo]
    link_groups: list[LinkGroupInfo]
    domains: list[Labelled]
    world_types: list[WorldTypeInfo]
    chronicle_kinds: list[Labelled]
    creature_traits: list[Labelled]
    passions: list[Labelled]
