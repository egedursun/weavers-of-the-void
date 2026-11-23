from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.agrarian import (
    AgrarianNodeView,
    BrandView,
    CentralPlaceView,
    CommonsView,
    CosmosAgrarianView,
    FamineLoreView,
    GameReserveView,
    IntensificationView,
    KeystoneView,
    LandRingView,
    PerennialView,
    PreparednessView,
    ReconstructionView,
    ReliefAidView,
    SoilNutrientView,
    UnbrandedWorkshopView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.agrarian import (
    BrandRow,
    CentralPlaceRow,
    CommonsRow,
    FamineLoreRow,
    GameReserveRow,
    IntensificationRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    ReconstructionRow,
    ReliefAidRow,
    SoilNutrientRow,
)
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.node import NodeKind

router = APIRouter(tags=["agrarian"])
NodeId = Annotated[int, Path(ge=1)]
COSMOS_AID = 40
NUTRIENT_ORDER = tuple(NutrientKind)


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def ring_view(row: LandRingRow, refs: dict[int, NodeRef]) -> LandRingView:
    return LandRingView(
        region=ref(refs, row.region_entity_id),
        market=at(refs, row.market_entity_id),
        ring=row.ring,
        distance=row.distance,
        by_water=row.by_water,
        gap=row.gap,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def central_view(row: CentralPlaceRow, refs: dict[int, NodeRef]) -> CentralPlaceView:
    return CentralPlaceView(
        settlement=ref(refs, row.settlement_entity_id),
        rank=row.rank,
        catchment=row.catchment,
        served_by=at(refs, row.served_by_entity_id),
        centrality=row.centrality,
        updated_epoch=row.updated_epoch,
        locked=row.locked,
    )


def perennial_view(row: PerennialRow, refs: dict[int, NodeRef]) -> PerennialView:
    return PerennialView(
        id=row.id,
        region=ref(refs, row.region_entity_id),
        kind=row.kind,
        species=at(refs, row.species_entity_id),
        owner=at(refs, row.owner_node_id),
        area=row.area,
        maturity=row.maturity,
        mature_epochs=row.mature_epochs,
        condition=row.condition,
        planted_epoch=row.planted_epoch,
        felled_epoch=row.felled_epoch,
        locked=row.locked,
    )


def commons_view(row: CommonsRow, refs: dict[int, NodeRef]) -> CommonsView:
    return CommonsView(
        id=row.id,
        region=ref(refs, row.region_entity_id),
        kind=row.kind,
        rule=row.rule,
        condition=row.condition,
        use=row.use,
        steward=at(refs, row.steward_entity_id),
        encloser=at(refs, row.encloser_node_id),
        enclosed_epoch=row.enclosed_epoch,
        dispossessed=row.dispossessed,
        quota=row.quota,
        licence_price=row.licence_price,
        officials=row.officials,
        since_epoch=row.since_epoch,
        locked=row.locked,
    )


def reserve_view(row: GameReserveRow, refs: dict[int, NodeRef]) -> GameReserveView:
    return GameReserveView(
        id=row.id,
        region=ref(refs, row.region_entity_id),
        holder=at(refs, row.holder_node_id),
        species=at(refs, row.species_entity_id),
        strictness=row.strictness,
        poaching=row.poaching,
        resentment=row.resentment,
        since_epoch=row.since_epoch,
        locked=row.locked,
    )


def aid_view(row: ReliefAidRow, refs: dict[int, NodeRef]) -> ReliefAidView:
    return ReliefAidView(
        id=row.id,
        event=at(refs, row.event_entity_id),
        giver=ref(refs, row.giver_node_id),
        receiver=ref(refs, row.receiver_entity_id),
        kind=row.kind,
        amount=row.amount,
        god=at(refs, row.god_node_id),
        refused=row.refused,
        epoch=row.epoch,
        locked=row.locked,
    )


def rebuild_view(row: ReconstructionRow, refs: dict[int, NodeRef]) -> ReconstructionView:
    return ReconstructionView(
        id=row.id,
        settlement=ref(refs, row.settlement_entity_id),
        cause=row.cause,
        plan=row.plan,
        cost=row.cost,
        paid=row.paid,
        progress=row.progress,
        planner=at(refs, row.planner_entity_id),
        seized_by=at(refs, row.seized_by_node_id),
        seized=row.seized,
        started_epoch=row.started_epoch,
        finished_epoch=row.finished_epoch,
        locked=row.locked,
    )


def keystone_view(row: KeystoneResourceRow, refs: dict[int, NodeRef]) -> KeystoneView:
    return KeystoneView(
        id=row.id,
        world=ref(refs, row.world_id),
        name=row.name,
        producer=at(refs, row.producer_entity_id),
        source=at(refs, row.source_region_entity_id),
        commodity=row.commodity,
        use=row.use,
        cult=at(refs, row.cult_entity_id),
        controller=at(refs, row.controller_entity_id),
        harvest=row.harvest,
        supply=row.supply,
        price=row.price,
        designated_epoch=row.designated_epoch,
        designated_by=at(refs, row.designated_by_son_id),
        locked=row.locked,
    )


def brand_view(row: BrandRow, workshop: WorkshopRow, refs: dict[int, NodeRef]) -> BrandView:
    return BrandView(
        id=row.id,
        workshop_id=row.workshop_id,
        workshop_kind=workshop.kind,
        community=ref(refs, row.community_entity_id),
        owner=at(refs, row.owner_node_id),
        name=row.name,
        reputation=row.reputation,
        quality=row.quality,
        renowned=row.renowned,
        counterfeits=row.counterfeits,
        since_epoch=row.since_epoch,
        locked=row.locked,
    )


def work_view(row: PreparednessRow, refs: dict[int, NodeRef]) -> PreparednessView:
    return PreparednessView(
        settlement=ref(refs, row.settlement_entity_id),
        kind=row.kind,
        level=row.level,
        condition=row.condition,
        averted=row.averted,
        built_epoch=row.built_epoch,
        locked=row.locked,
    )


def keystone_ids(row: KeystoneResourceRow) -> tuple[int | None, ...]:
    return (row.world_id, row.producer_entity_id, row.source_region_entity_id, row.cult_entity_id, row.controller_entity_id, row.designated_by_son_id)


async def world_of(session: AsyncSession, node_id: int) -> int | None:
    if await session.get(WorldRow, node_id) is not None:
        return node_id
    entity = await session.get(EntityRow, node_id)
    return entity.world_id if entity is not None else None


async def brands_with(session: AsyncSession, *conditions: ColumnElement[bool]) -> list[tuple[BrandRow, WorkshopRow]]:
    rows = await session.execute(
        select(BrandRow, WorkshopRow).join(WorkshopRow, WorkshopRow.id == BrandRow.workshop_id).where(*conditions).order_by(BrandRow.id)
    )
    return [(brand, workshop) for brand, workshop in rows.all()]


@router.get("/agrarian/of/{node_id}", response_model=AgrarianNodeView)
async def node_agrarian(services: ServicesDep, node_id: NodeId) -> AgrarianNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        world_id = await world_of(session, node_id)
        ring = await session.get(LandRingRow, node_id)
        nutrients = sorted(
            await session.scalars(select(SoilNutrientRow).where(SoilNutrientRow.region_entity_id == node_id)),
            key=lambda row: NUTRIENT_ORDER.index(row.nutrient),
        )
        intensity = await session.get(IntensificationRow, node_id)
        perennials = list(
            await session.scalars(
                select(PerennialRow).where(or_(PerennialRow.region_entity_id == node_id, PerennialRow.owner_node_id == node_id)).order_by(PerennialRow.id)
            )
        )
        commons = list(
            await session.scalars(
                select(CommonsRow)
                .where(or_(CommonsRow.region_entity_id == node_id, CommonsRow.steward_entity_id == node_id, CommonsRow.encloser_node_id == node_id))
                .order_by(CommonsRow.id)
            )
        )
        reserves = list(
            await session.scalars(
                select(GameReserveRow)
                .where(or_(GameReserveRow.region_entity_id == node_id, GameReserveRow.holder_node_id == node_id, GameReserveRow.species_entity_id == node_id))
                .order_by(GameReserveRow.id)
            )
        )
        famine = await session.get(FamineLoreRow, node_id)
        central = await session.get(CentralPlaceRow, node_id)
        works = list(await session.scalars(select(PreparednessRow).where(PreparednessRow.settlement_entity_id == node_id).order_by(PreparednessRow.kind)))
        aid = list(
            await session.scalars(
                select(ReliefAidRow)
                .where(
                    or_(
                        ReliefAidRow.receiver_entity_id == node_id,
                        ReliefAidRow.giver_node_id == node_id,
                        ReliefAidRow.god_node_id == node_id,
                        ReliefAidRow.event_entity_id == node_id,
                    )
                )
                .order_by(ReliefAidRow.epoch.desc(), ReliefAidRow.id.desc())
            )
        )
        rebuilds = list(
            await session.scalars(
                select(ReconstructionRow)
                .where(
                    or_(
                        ReconstructionRow.settlement_entity_id == node_id,
                        ReconstructionRow.seized_by_node_id == node_id,
                        ReconstructionRow.planner_entity_id == node_id,
                    )
                )
                .order_by(ReconstructionRow.id.desc())
            )
        )
        keystones = list(
            await session.scalars(
                select(KeystoneResourceRow)
                .where(
                    or_(
                        KeystoneResourceRow.world_id == node_id,
                        KeystoneResourceRow.producer_entity_id == node_id,
                        KeystoneResourceRow.source_region_entity_id == node_id,
                        KeystoneResourceRow.cult_entity_id == node_id,
                        KeystoneResourceRow.controller_entity_id == node_id,
                    )
                )
                .order_by(KeystoneResourceRow.id)
            )
        )
        brands = await brands_with(session, or_(BrandRow.community_entity_id == node_id, BrandRow.owner_node_id == node_id))
        branded = {brand.workshop_id for brand, _ in brands}
        workshops = [
            row
            for row in await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id == node_id).order_by(WorkshopRow.id))
            if row.id not in branded
        ]
        refs = await refs_of(
            session,
            [
                world_id,
                *((ring.region_entity_id, ring.market_entity_id) if ring is not None else ()),
                *(item for row in perennials for item in (row.region_entity_id, row.species_entity_id, row.owner_node_id)),
                *(item for row in commons for item in (row.region_entity_id, row.steward_entity_id, row.encloser_node_id)),
                *(item for row in reserves for item in (row.region_entity_id, row.holder_node_id, row.species_entity_id)),
                *((famine.people_entity_id,) if famine is not None else ()),
                *((central.settlement_entity_id, central.served_by_entity_id) if central is not None else ()),
                *(row.settlement_entity_id for row in works),
                *(item for row in aid for item in (row.event_entity_id, row.giver_node_id, row.receiver_entity_id, row.god_node_id)),
                *(item for row in rebuilds for item in (row.settlement_entity_id, row.planner_entity_id, row.seized_by_node_id)),
                *(item for row in keystones for item in keystone_ids(row)),
                *(item for brand, _ in brands for item in (brand.community_entity_id, brand.owner_node_id)),
            ],
        )
        return AgrarianNodeView(
            node=own[node_id],
            world=at(refs, world_id),
            ring=ring_view(ring, refs) if ring is not None else None,
            nutrients=[
                SoilNutrientView(nutrient=row.nutrient, stock=row.stock, trend=row.trend, updated_epoch=row.updated_epoch, locked=row.locked)
                for row in nutrients
            ],
            intensity=(
                IntensificationView(
                    pressure=intensity.pressure,
                    intensity=intensity.intensity,
                    research_boost=intensity.research_boost,
                    updated_epoch=intensity.updated_epoch,
                    locked=intensity.locked,
                )
                if intensity is not None
                else None
            ),
            perennials=[perennial_view(row, refs) for row in perennials],
            commons=[commons_view(row, refs) for row in commons],
            reserves=[reserve_view(row, refs) for row in reserves],
            famine=(
                FamineLoreView(
                    people=ref(refs, famine.people_entity_id),
                    memory=famine.memory,
                    famine_foods=famine.famine_foods,
                    storage=famine.storage,
                    updated_epoch=famine.updated_epoch,
                    locked=famine.locked,
                )
                if famine is not None
                else None
            ),
            central_place=central_view(central, refs) if central is not None else None,
            works=[work_view(row, refs) for row in works],
            aid=[aid_view(row, refs) for row in aid],
            rebuilds=[rebuild_view(row, refs) for row in rebuilds],
            keystones=[keystone_view(row, refs) for row in keystones],
            brands=[brand_view(brand, workshop, refs) for brand, workshop in brands],
            workshops=[UnbrandedWorkshopView(id=row.id, kind=row.kind, level=row.level) for row in workshops],
        )


@router.get("/agrarian/cosmos", response_model=CosmosAgrarianView)
async def cosmos_agrarian(services: ServicesDep) -> CosmosAgrarianView:
    async with reader(services) as session:
        rings = list(await session.scalars(select(LandRingRow).order_by(LandRingRow.gap.desc(), LandRingRow.region_entity_id)))
        central = list(await session.scalars(select(CentralPlaceRow).order_by(CentralPlaceRow.centrality.desc(), CentralPlaceRow.settlement_entity_id)))
        keystones = list(await session.scalars(select(KeystoneResourceRow).order_by(KeystoneResourceRow.id)))
        brands = await brands_with(session)
        aid = list(await session.scalars(select(ReliefAidRow).order_by(ReliefAidRow.epoch.desc(), ReliefAidRow.id.desc()).limit(COSMOS_AID)))
        rebuilds = list(await session.scalars(select(ReconstructionRow).where(ReconstructionRow.finished_epoch.is_(None)).order_by(ReconstructionRow.id)))
        commons = list(await session.scalars(select(CommonsRow).order_by(CommonsRow.condition, CommonsRow.id)))
        reserves = list(await session.scalars(select(GameReserveRow).order_by(GameReserveRow.resentment.desc(), GameReserveRow.id)))
        refs = await refs_of(
            session,
            [
                *(item for row in rings for item in (row.region_entity_id, row.market_entity_id)),
                *(item for row in central for item in (row.settlement_entity_id, row.served_by_entity_id)),
                *(item for row in keystones for item in keystone_ids(row)),
                *(item for brand, _ in brands for item in (brand.community_entity_id, brand.owner_node_id)),
                *(item for row in aid for item in (row.event_entity_id, row.giver_node_id, row.receiver_entity_id, row.god_node_id)),
                *(item for row in rebuilds for item in (row.settlement_entity_id, row.planner_entity_id, row.seized_by_node_id)),
                *(item for row in commons for item in (row.region_entity_id, row.steward_entity_id, row.encloser_node_id)),
                *(item for row in reserves for item in (row.region_entity_id, row.holder_node_id, row.species_entity_id)),
            ],
        )
        return CosmosAgrarianView(
            rings=[ring_view(row, refs) for row in rings],
            central_places=[central_view(row, refs) for row in central],
            keystones=[keystone_view(row, refs) for row in keystones],
            brands=[brand_view(brand, workshop, refs) for brand, workshop in brands],
            aid=[aid_view(row, refs) for row in aid],
            rebuilds=[rebuild_view(row, refs) for row in rebuilds],
            commons=[commons_view(row, refs) for row in commons],
            reserves=[reserve_view(row, refs) for row in reserves],
        )
