from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.museums import GardenView, GroundsNodeView, MuseumCollectionView, MuseumPieceView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.domain.enums.entity import EntityType

router = APIRouter(tags=["museums"])
NodeId = Annotated[int, Path(ge=1)]
NO_KEEPER = "Only a people, a town, a realm or another community keeps collections and gardens; this thing keeps none and lives in no town."
KEEPERS = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.POLITY, EntityType.FACTION, EntityType.CULT})


@router.get("/grounds/of/{node_id}", response_model=GroundsNodeView)
async def node_grounds(services: ServicesDep, node_id: NodeId) -> GroundsNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        keeper = entity if entity is not None and entity.entity_type in KEEPERS else None
        if keeper is None and entity is not None and entity.location_id is not None:
            place = await session.get(EntityRow, entity.location_id)
            keeper = place if place is not None and place.entity_type in KEEPERS else None
        if keeper is None:
            return GroundsNodeView(node=own[node_id], keeper=None, collections=[], gardens=[], absent_reason=NO_KEEPER)
        kept = select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == keeper.id).order_by(MuseumCollectionRow.id)
        hoards = list(await session.scalars(kept))
        pieces = list(
            await session.scalars(select(MuseumPieceRow).where(MuseumPieceRow.collection_id.in_([hoard.id for hoard in hoards])).order_by(MuseumPieceRow.id))
        )
        gardens = list(await session.scalars(select(GardenRow).where(GardenRow.settlement_entity_id == keeper.id).order_by(GardenRow.id)))
        ids = {keeper.id}
        ids |= {item for hoard in hoards for item in (hoard.structure_entity_id,) if item}
        ids |= {item for piece in pieces for item in (piece.item_entity_id, piece.looted_from_entity_id, piece.returned_by_entity_id) if item}
        ids |= {item for garden in gardens for item in (garden.structure_entity_id, *garden.species) if item}
        refs = await node_refs(session, sorted(ids))
        return GroundsNodeView(
            node=own[node_id],
            keeper=refs.get(keeper.id),
            collections=[
                MuseumCollectionView(
                    id=hoard.id,
                    keeper=refs.get(hoard.keeper_entity_id),
                    structure=refs.get(hoard.structure_entity_id) if hoard.structure_entity_id else None,
                    kind=hoard.kind,
                    prestige=hoard.prestige,
                    founded_epoch=hoard.founded_epoch,
                    pieces=[
                        MuseumPieceView(
                            id=piece.id,
                            kind=piece.kind,
                            item=refs.get(piece.item_entity_id) if piece.item_entity_id else None,
                            fossil_bed_id=piece.fossil_bed_id,
                            acquired_epoch=piece.acquired_epoch,
                            looted_from=refs.get(piece.looted_from_entity_id) if piece.looted_from_entity_id else None,
                            returned_epoch=piece.returned_epoch,
                            returned_by=refs.get(piece.returned_by_entity_id) if piece.returned_by_entity_id else None,
                            locked=list(piece.locked),
                        )
                        for piece in pieces
                        if piece.collection_id == hoard.id
                    ],
                    locked=list(hoard.locked),
                )
                for hoard in hoards
            ],
            gardens=[
                GardenView(
                    id=garden.id,
                    town=refs.get(garden.settlement_entity_id),
                    structure=refs.get(garden.structure_entity_id) if garden.structure_entity_id else None,
                    kind=garden.kind,
                    species=[refs[item] for item in garden.species if item in refs],
                    upkeep=garden.upkeep,
                    condition=garden.condition,
                    unpaid_epochs=garden.unpaid_epochs,
                    founded_epoch=garden.founded_epoch,
                    locked=list(garden.locked),
                )
                for garden in gardens
            ],
            absent_reason=None,
        )
