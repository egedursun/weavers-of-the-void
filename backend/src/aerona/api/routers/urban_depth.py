from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.urban_depth import (
    ConvoyView,
    CoverageView,
    CrimeStanceView,
    DistrictChoice,
    DistrictUrbanView,
    FleetView,
    MarketPlayView,
    NodeUrbanView,
    OrderLawView,
    PayrollView,
    PlacementView,
    RacketView,
    TownUrbanView,
    TradingPostView,
    TribunalView,
    TurfView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import (
    ConvoyRow,
    CrimeStanceRow,
    DistrictServiceRow,
    FleetRow,
    MarketPlayRow,
    OrderLawRow,
    PayrollRow,
    RacketRow,
    TradingPostRow,
    TribunalRow,
    TurfRow,
)

router = APIRouter(tags=["urban"])
NodeId = Annotated[int, Path(ge=1)]
DISTRICT_KEYS = ("housing", "desirability", "land_value")
TOWN_KEYS = ("morphology", "homeless")


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def turf_views(session: AsyncSession, rows: list[TurfRow]) -> list[TurfView]:
    districts = {row.id: row for row in await session.scalars(select(DistrictRow).where(DistrictRow.id.in_([item.district_id for item in rows])))}
    refs = await refs_for(
        session,
        [item for row in rows for item in (row.faction_entity_id, districts[row.district_id].settlement_entity_id if row.district_id in districts else None)],
    )
    return [
        TurfView(
            district_id=row.district_id,
            district_kind=districts[row.district_id].kind if row.district_id in districts else None,
            town=at(refs, districts[row.district_id].settlement_entity_id) if row.district_id in districts else None,
            faction=at(refs, row.faction_entity_id),
            strength=row.strength,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def district_views(session: AsyncSession, settlement_id: int) -> list[DistrictUrbanView]:
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement_id).order_by(DistrictRow.id)))
    ids = [district.id for district in districts]
    services: dict[int, list[CoverageView]] = {district_id: [] for district_id in ids}
    for row in await session.scalars(select(DistrictServiceRow).where(DistrictServiceRow.district_id.in_(ids)).order_by(DistrictServiceRow.service)):
        services[row.district_id].append(CoverageView(service=row.service, coverage=row.coverage, epoch=row.epoch, locked=list(row.locked)))
    turf = await turf_views(
        session, list(await session.scalars(select(TurfRow).where(TurfRow.district_id.in_(ids)).order_by(TurfRow.district_id, TurfRow.faction_entity_id)))
    )
    return [
        DistrictUrbanView(
            id=district.id,
            kind=district.kind,
            level=district.level,
            housing=district.housing,
            desirability=district.desirability,
            land_value=district.land_value,
            services=services[district.id],
            turf=[item for item in turf if item.district_id == district.id],
            locked=[key for key in district.locked if key in DISTRICT_KEYS],
        )
        for district in districts
    ]


async def placement_of(session: AsyncSession, node_id: int) -> PlacementView | None:
    profile = await session.get(StructureProfileRow, node_id)
    building = await session.get(EntityRow, node_id)
    if profile is None or building is None or building.location_id is None:
        return None
    districts = await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == building.location_id).order_by(DistrictRow.id))
    return PlacementView(district_id=profile.district_id, choices=[DistrictChoice(id=row.id, kind=row.kind, level=row.level) for row in districts])


async def racket_views(session: AsyncSession, node_id: int) -> list[RacketView]:
    rows = list(
        await session.scalars(
            select(RacketRow)
            .where(or_(RacketRow.faction_entity_id == node_id, RacketRow.settlement_entity_id == node_id))
            .order_by(RacketRow.faction_entity_id, RacketRow.settlement_entity_id, RacketRow.racket)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.faction_entity_id, row.settlement_entity_id)])
    return [
        RacketView(
            faction=at(refs, row.faction_entity_id),
            settlement=at(refs, row.settlement_entity_id),
            racket=row.racket,
            income=row.income,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def payroll_views(session: AsyncSession, node_id: int) -> list[PayrollView]:
    rows = list(
        await session.scalars(
            select(PayrollRow)
            .where(or_(PayrollRow.faction_entity_id == node_id, PayrollRow.official_entity_id == node_id))
            .order_by(PayrollRow.official_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.faction_entity_id, row.official_entity_id)])
    return [
        PayrollView(
            faction=at(refs, row.faction_entity_id),
            official=at(refs, row.official_entity_id),
            bribe=row.bribe,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def stance_views(session: AsyncSession, node_id: int) -> list[CrimeStanceView]:
    rows = list(
        await session.scalars(
            select(CrimeStanceRow)
            .where(or_(CrimeStanceRow.polity_entity_id == node_id, CrimeStanceRow.faction_entity_id == node_id))
            .order_by(CrimeStanceRow.polity_entity_id, CrimeStanceRow.faction_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.polity_entity_id, row.faction_entity_id)])
    return [
        CrimeStanceView(
            polity=at(refs, row.polity_entity_id),
            faction=at(refs, row.faction_entity_id),
            stance=row.stance,
            strength=row.strength,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def tribunal_views(session: AsyncSession, node_id: int) -> list[TribunalView]:
    rows = list(
        await session.scalars(
            select(TribunalRow).where(or_(TribunalRow.faction_entity_id == node_id, TribunalRow.accused_entity_id == node_id)).order_by(TribunalRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.faction_entity_id, row.accused_entity_id)])
    return [
        TribunalView(
            id=row.id,
            order=at(refs, row.faction_entity_id),
            accused=at(refs, row.accused_entity_id),
            law=row.law,
            verdict=row.verdict,
            fine=row.fine,
            epoch=row.epoch,
        )
        for row in rows
    ]


async def post_views(session: AsyncSession, node_id: int) -> list[TradingPostView]:
    rows = list(
        await session.scalars(
            select(TradingPostRow)
            .where(or_(TradingPostRow.structure_entity_id == node_id, TradingPostRow.owner_entity_id == node_id, TradingPostRow.host_settlement_id == node_id))
            .order_by(TradingPostRow.structure_entity_id)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.structure_entity_id, row.owner_entity_id, row.host_settlement_id)])
    return [
        TradingPostView(
            structure=at(refs, row.structure_entity_id),
            owner=at(refs, row.owner_entity_id),
            host=at(refs, row.host_settlement_id),
            informants=row.informants,
            goods=row.goods,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def convoy_views(session: AsyncSession, node_id: int) -> list[ConvoyView]:
    rows = list(
        await session.scalars(
            select(ConvoyRow).where(or_(ConvoyRow.route_entity_id == node_id, ConvoyRow.owner_entity_id == node_id)).order_by(ConvoyRow.id.desc())
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.owner_entity_id, row.route_entity_id, row.region_entity_id)])
    return [
        ConvoyView(
            id=row.id,
            owner=at(refs, row.owner_entity_id),
            route=at(refs, row.route_entity_id),
            cargo=dict(row.cargo),
            preservation=row.preservation,
            animals=row.animals,
            vehicles=row.vehicles,
            guards=row.guards,
            passengers=dict(row.passengers),
            season=row.season,
            status=row.status,
            region=at(refs, row.region_entity_id),
            capacity=row.capacity,
            departed_epoch=row.departed_epoch,
            arrived_epoch=row.arrived_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def fleet_views(session: AsyncSession, node_id: int) -> list[FleetView]:
    rows = list(await session.scalars(select(FleetRow).where(FleetRow.owner_entity_id == node_id).order_by(FleetRow.kind)))
    refs = await refs_for(session, [node_id])
    return [
        FleetView(owner=at(refs, row.owner_entity_id), kind=row.kind, count=row.count, age=row.age, condition=row.condition, locked=list(row.locked))
        for row in rows
    ]


async def play_views(session: AsyncSession, node_id: int) -> list[MarketPlayView]:
    rows = list(
        await session.scalars(
            select(MarketPlayRow)
            .where(or_(MarketPlayRow.holder_entity_id == node_id, MarketPlayRow.settlement_entity_id == node_id))
            .order_by(MarketPlayRow.settlement_entity_id, MarketPlayRow.commodity)
        )
    )
    refs = await refs_for(session, [item for row in rows for item in (row.holder_entity_id, row.settlement_entity_id)])
    return [
        MarketPlayView(
            holder=at(refs, row.holder_entity_id),
            settlement=at(refs, row.settlement_entity_id),
            commodity=row.commodity,
            play=row.play,
            strength=row.strength,
            since_epoch=row.since_epoch,
            until_epoch=row.until_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


@router.get("/urban/of/{node_id}", response_model=NodeUrbanView)
async def node_urban(services: ServicesDep, node_id: NodeId) -> NodeUrbanView:
    async with reader(services) as session:
        refs = await node_refs(session, [node_id])
        if node_id not in refs:
            raise NotFoundError("No such thing.")
        profile = await session.get(SettlementProfileRow, node_id)
        turf = list(await session.scalars(select(TurfRow).where(TurfRow.faction_entity_id == node_id).order_by(TurfRow.district_id)))
        return NodeUrbanView(
            node=refs[node_id],
            town=TownUrbanView(morphology=profile.morphology, homeless=profile.homeless, locked=[key for key in profile.locked if key in TOWN_KEYS])
            if profile is not None
            else None,
            districts=await district_views(session, node_id) if profile is not None else [],
            placement=await placement_of(session, node_id),
            turf=await turf_views(session, turf),
            rackets=await racket_views(session, node_id),
            payroll=await payroll_views(session, node_id),
            stances=await stance_views(session, node_id),
            laws=[
                OrderLawView(law=row.law, strength=row.strength, locked=list(row.locked))
                for row in await session.scalars(select(OrderLawRow).where(OrderLawRow.faction_entity_id == node_id).order_by(OrderLawRow.law))
            ],
            tribunals=await tribunal_views(session, node_id),
            posts=await post_views(session, node_id),
            convoys=await convoy_views(session, node_id),
            fleets=await fleet_views(session, node_id),
            plays=await play_views(session, node_id),
        )
