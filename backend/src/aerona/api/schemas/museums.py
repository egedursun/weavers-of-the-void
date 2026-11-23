from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import HoardKind, PieceKind


class MuseumPieceView(ApiModel):
    id: int
    kind: PieceKind
    item: NodeRef | None
    fossil_bed_id: int | None
    acquired_epoch: int
    looted_from: NodeRef | None
    polity: NodeRef | None
    returned_epoch: int | None
    returned_by: NodeRef | None
    locked: list[str]


class MuseumCollectionView(ApiModel):
    id: int
    keeper: NodeRef | None
    structure: NodeRef | None
    kind: HoardKind
    prestige: int
    founded_epoch: int
    pieces: list[MuseumPieceView]
    locked: list[str]


class GardenView(ApiModel):
    id: int
    town: NodeRef | None
    structure: NodeRef | None
    kind: GardenKind
    species: list[NodeRef]
    upkeep: int
    condition: int
    unpaid_epochs: int
    founded_epoch: int
    locked: list[str]


class GroundsNodeView(ApiModel):
    node: NodeRef
    keeper: NodeRef | None
    collections: list[MuseumCollectionView]
    gardens: list[GardenView]
    absent_reason: str | None
