from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.foundations import current_epoch
from aerona.api.schemas.climes import (
    ClimesNodeView,
    CosmopolitanCultureView,
    LaunchWindowView,
    MonsoonSeasonView,
    OscillationView,
    RegionWindView,
    RoadMemberView,
    RoadRouteChoice,
    RoadValueView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import (
    ClimateOscillationRow,
    CosmopolitanCultureRow,
    CosmopolitanMemberRow,
    LaunchWindowRow,
    MonsoonSeasonRow,
    RegionWindRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.node import NodeKind
from aerona.engine.primitives.distance import RegionAtlas

router = APIRouter(tags=["climes"])
NodeId = Annotated[int, Path(ge=1)]


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def ref(refs: dict[int, NodeRef], node_id: int) -> NodeRef:
    return refs[node_id] if node_id in refs else NodeRef(id=node_id, kind=NodeKind.ENTITY, name="a lost record")


async def refs_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, sorted({value for value in ids if value is not None}))


def route_name(route: RouteRow, refs: dict[int, NodeRef]) -> str:
    return f"{ref(refs, route.world_a_id).name} to {ref(refs, route.world_b_id).name} by {spoken(route.method)}"


async def world_of(session: AsyncSession, node_id: int) -> int | None:
    if await session.get(WorldRow, node_id) is not None:
        return node_id
    entity = await session.get(EntityRow, node_id)
    return entity.world_id if entity is not None else None


@router.get("/climes/of/{node_id}", response_model=ClimesNodeView)
async def node_climes(services: ServicesDep, node_id: NodeId) -> ClimesNodeView:
    async with reader(services) as session:
        own = await node_refs(session, [node_id])
        if node_id not in own:
            raise NotFoundError("No such thing.")
        epoch = await current_epoch(session)
        world_id = await world_of(session, node_id)
        entity = await session.get(EntityRow, node_id)
        region_id = node_id if entity is not None and entity.entity_type is EntityType.REGION else (await RegionAtlas.load(session)).top_region(node_id)
        lands = (
            [region_id]
            if region_id is not None
            else list(await session.scalars(select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)))
            if world_id == node_id
            else []
        )
        winds = list(await session.scalars(select(RegionWindRow).where(RegionWindRow.region_entity_id.in_(lands)).order_by(RegionWindRow.region_entity_id)))
        monsoons = (
            list(await session.scalars(select(MonsoonSeasonRow).where(MonsoonSeasonRow.world_id == world_id).order_by(MonsoonSeasonRow.epoch.desc())))
            if world_id is not None
            else []
        )
        oscillation = await session.get(ClimateOscillationRow, world_id) if world_id is not None else None
        windows = (
            list(
                await session.scalars(
                    select(LaunchWindowRow)
                    .where(or_(LaunchWindowRow.from_world_id == world_id, LaunchWindowRow.to_world_id == world_id))
                    .order_by(LaunchWindowRow.from_world_id, LaunchWindowRow.to_world_id)
                )
            )
            if world_id is not None
            else []
        )
        touching = (
            list(await session.scalars(select(RouteRow).where(or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id)).order_by(RouteRow.id)))
            if world_id is not None
            else []
        )
        joined = select(CosmopolitanMemberRow.culture_id).where(CosmopolitanMemberRow.community_entity_id == node_id)
        cultures = list(
            await session.scalars(
                select(CosmopolitanCultureRow)
                .where(or_(CosmopolitanCultureRow.route_id.in_([route.id for route in touching]), CosmopolitanCultureRow.id.in_(joined)))
                .order_by(CosmopolitanCultureRow.id)
            )
        )
        members = list(
            await session.scalars(
                select(CosmopolitanMemberRow)
                .where(CosmopolitanMemberRow.culture_id.in_([row.id for row in cultures]))
                .order_by(CosmopolitanMemberRow.share.desc(), CosmopolitanMemberRow.community_entity_id)
            )
        )
        routes = {route.id: route for route in touching}
        for culture in cultures:
            if culture.route_id is not None and culture.route_id not in routes:
                found = await session.get(RouteRow, culture.route_id)
                if found is not None:
                    routes[found.id] = found
        refs = await refs_of(
            session,
            [
                node_id,
                world_id,
                region_id,
                *(row.region_entity_id for row in winds),
                *(item for row in windows for item in (row.from_world_id, row.to_world_id)),
                *(item for route in routes.values() for item in (route.world_a_id, route.world_b_id)),
                *(row.lingua_franca_entity_id for row in cultures),
                *(row.community_entity_id for row in members),
            ],
        )
    choices = {route.id: RoadRouteChoice(id=route.id, name=route_name(route, refs)) for route in routes.values()}
    return ClimesNodeView(
        node=ref(refs, node_id),
        world=at(refs, world_id),
        region=at(refs, region_id),
        epoch=epoch,
        winds=[
            RegionWindView(
                region=ref(refs, row.region_entity_id),
                band=row.band,
                summer_band=row.summer_band,
                wind_from=row.wind_from,
                strength=row.strength,
                windward=row.windward,
                shadow=row.shadow,
                monsoon=row.monsoon,
                upwelling=row.upwelling,
                read_epoch=row.read_epoch,
                locked=row.locked,
            )
            for row in winds
        ],
        monsoons=[MonsoonSeasonView(epoch=row.epoch, strength=row.strength, failed=row.failed, locked=row.locked) for row in monsoons],
        oscillation=OscillationView(
            phase=oscillation.phase, period=oscillation.period, step=oscillation.step, strength=oscillation.strength, locked=oscillation.locked
        )
        if oscillation is not None
        else None,
        windows=[
            LaunchWindowView(
                from_world=ref(refs, row.from_world_id),
                to_world=ref(refs, row.to_world_id),
                synodic=row.synodic,
                offset=row.offset,
                open=row.open,
                locked=row.locked,
            )
            for row in windows
        ],
        cultures=[
            CosmopolitanCultureView(
                id=row.id,
                route=choices.get(row.route_id) if row.route_id is not None else None,
                name=row.name,
                lingua_franca=at(refs, row.lingua_franca_entity_id),
                strength=row.strength,
                values=[RoadValueView(axis=ValueAxis(axis), value=int(value)) for axis, value in sorted(row.values.items())],
                formed_epoch=row.formed_epoch,
                members=[
                    RoadMemberView(community=ref(refs, member.community_entity_id), share=member.share, joined_epoch=member.joined_epoch, locked=member.locked)
                    for member in members
                    if member.culture_id == row.id
                ],
                locked=row.locked,
            )
            for row in cultures
        ],
        routes=[choices[route.id] for route in touching],
    )
