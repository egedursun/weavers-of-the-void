from collections.abc import Iterable, Mapping
from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.gatherings import (
    CollectionView,
    ContentView,
    DigStageView,
    DigView,
    FeatureView,
    GatheringView,
    GuestView,
    HistoryDetail,
    HistoryMemberView,
    HistoryPage,
    HolderView,
    IncidentLine,
    LifeLogEntry,
    LifeLogView,
    NodeGatheringsView,
    RoomView,
    SeasonOption,
    SiteView,
    StorytellerView,
    TensionPoint,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionPlaceRow, CollectionRow, GatheringGuestRow, GatheringRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sites import BattlefieldFeatureRow, ExcavationRow, ExcavationStageRow, RoomContentRow, SiteHolderRow, SiteRoomRow
from aerona.db.tables.storyteller import StorytellerRow, TensionRecordRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.storyteller import SpontaneousKind, StorytellerProfile, TensionBand
from aerona.engine.primitives.manual import manual_context
from aerona.engine.sites.digs import diggable
from aerona.engine.sites.rooms import layout_of

router = APIRouter(tags=["gatherings"])
Id = Annotated[int, Path(ge=1)]
PAGE_MAX = 200


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def collection_names(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = sorted({value for value in ids if value is not None})
    if not wanted:
        return {}
    return {row.id: row.name for row in await session.scalars(select(CollectionRow).where(CollectionRow.id.in_(wanted)))}


async def battle_names(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = sorted({value for value in ids if value is not None})
    if not wanted:
        return {}
    named = await session.execute(
        select(BattleRow.id, EntityRow.name).join(EntityRow, EntityRow.id == BattleRow.record_entity_id).where(BattleRow.id.in_(wanted))
    )
    return {int(battle_id): str(name) for battle_id, name in named}


async def gathering_views(session: AsyncSession, rows: list[GatheringRow]) -> list[GatheringView]:
    ids = [row.id for row in rows]
    guests = (
        list(await session.scalars(select(GatheringGuestRow).where(GatheringGuestRow.gathering_id.in_(ids)).order_by(GatheringGuestRow.node_id))) if ids else []
    )
    wanted = {
        *(guest.node_id for guest in guests),
        *(row.host_node_id for row in rows),
        *(node for row in rows for node in (row.place_entity_id, row.honoured_node_id, row.tradition_entity_id) if node is not None),
    }
    refs = await node_refs(session, wanted)
    histories = await collection_names(session, [row.collection_id for row in rows])
    worlds = {row.world_id for row in rows if row.world_id is not None}
    seasons: dict[int, list[SeasonOption]] = {}
    if worlds:
        for season in await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id.in_(worlds)).order_by(WorldSeasonRow.position)):
            seasons.setdefault(season.world_id, []).append(SeasonOption(position=season.position, name=season.name))
    return [
        GatheringView(
            id=row.id,
            kind=row.kind,
            status=row.status,
            outcome=row.outcome,
            milestone=row.milestone,
            host=ref(refs, row.host_node_id),
            place=ref(refs, row.place_entity_id),
            honoured=ref(refs, row.honoured_node_id),
            tradition=ref(refs, row.tradition_entity_id),
            collection_id=row.collection_id,
            collection_name=histories.get(row.collection_id or 0),
            epoch=row.epoch,
            year=row.year,
            season=row.season,
            season_name=next((option.name for option in seasons.get(row.world_id or 0, []) if option.position == row.season), None),
            seasons=seasons.get(row.world_id or 0, []),
            cost=row.cost,
            food=row.food,
            prestige=row.prestige,
            by_player=row.by_player,
            note=row.note,
            locked=list(row.locked or []),
            guests=[
                GuestView(
                    node=ref(refs, guest.node_id),
                    role=guest.role,
                    reason=guest.reason,
                    invited=guest.invited,
                    attended=guest.attended,
                    harmed=guest.harmed,
                    locked=guest.locked,
                )
                for guest in guests
                if guest.gathering_id == row.id
            ],
        )
        for row in rows
    ]


@router.get("/gatherings/of/{node_id}", response_model=NodeGatheringsView)
async def gatherings_of(services: ServicesDep, node_id: Id) -> NodeGatheringsView:
    async with reader(services) as session:
        hosted = list(
            await session.scalars(select(GatheringRow).where(GatheringRow.host_node_id == node_id).order_by(GatheringRow.epoch.desc(), GatheringRow.id.desc()))
        )
        came = select(GatheringGuestRow.gathering_id).where(GatheringGuestRow.node_id == node_id, GatheringGuestRow.attended.is_(True))
        attended = list(
            await session.scalars(
                select(GatheringRow)
                .where(GatheringRow.id.in_(came), GatheringRow.host_node_id != node_id)
                .order_by(GatheringRow.epoch.desc(), GatheringRow.id.desc())
            )
        )
        return NodeGatheringsView(node_id=node_id, hosted=await gathering_views(session, hosted), attended=await gathering_views(session, attended))


async def collection_views(session: AsyncSession, rows: Iterable[CollectionRow]) -> list[CollectionView]:
    rows = list(rows)
    ids = [row.id for row in rows]
    members = (
        dict(
            (
                await session.execute(
                    select(CollectionMemberRow.collection_id, func.count())
                    .where(CollectionMemberRow.collection_id.in_(ids))
                    .group_by(CollectionMemberRow.collection_id)
                )
            ).all()
        )
        if ids
        else {}
    )
    places = (
        dict(
            (
                await session.execute(
                    select(CollectionPlaceRow.collection_id, func.count())
                    .where(CollectionPlaceRow.collection_id.in_(ids))
                    .group_by(CollectionPlaceRow.collection_id)
                )
            ).all()
        )
        if ids
        else {}
    )
    return [
        CollectionView(
            id=row.id,
            kind=row.kind,
            name=row.name,
            world_id=row.world_id,
            start_epoch=row.start_epoch,
            end_epoch=row.end_epoch,
            parent_id=row.parent_id,
            note=row.note,
            locked=list(row.locked or []),
            members=int(members.get(row.id, 0)),
            places=int(places.get(row.id, 0)),
        )
        for row in rows
    ]


@router.get("/histories", response_model=HistoryPage)
async def histories(
    services: ServicesDep,
    *,
    kind: Annotated[CollectionKind | None, Query()] = None,
    world_id: Annotated[int | None, Query(ge=1)] = None,
    node_id: Annotated[int | None, Query(ge=1)] = None,
    place_id: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=PAGE_MAX)] = 40,
) -> HistoryPage:
    async with reader(services) as session:
        statement = select(CollectionRow)
        if kind is not None:
            statement = statement.where(CollectionRow.kind == kind)
        if world_id is not None:
            statement = statement.where(CollectionRow.world_id == world_id)
        if node_id is not None:
            statement = statement.where(CollectionRow.id.in_(select(CollectionMemberRow.collection_id).where(CollectionMemberRow.node_id == node_id)))
        if place_id is not None:
            statement = statement.where(CollectionRow.id.in_(select(CollectionPlaceRow.collection_id).where(CollectionPlaceRow.place_entity_id == place_id)))
        total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        rows = await session.scalars(statement.order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc()).offset(offset).limit(limit))
        return HistoryPage(items=await collection_views(session, rows), total=total)


@router.get("/histories/of/{node_id}", response_model=LifeLogView)
async def life_log(services: ServicesDep, node_id: Id) -> LifeLogView:
    async with reader(services) as session:
        rows = (
            await session.execute(
                select(CollectionRow, CollectionMemberRow.role)
                .join(CollectionMemberRow, CollectionMemberRow.collection_id == CollectionRow.id)
                .where(CollectionMemberRow.node_id == node_id)
                .order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc())
            )
        ).all()
        places = list(
            await session.scalars(
                select(CollectionRow)
                .join(CollectionPlaceRow, CollectionPlaceRow.collection_id == CollectionRow.id)
                .where(CollectionPlaceRow.place_entity_id == node_id)
                .order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc())
            )
        )
        views = {view.id: view for view in await collection_views(session, [row for row, _ in rows] + places)}
        entries = [LifeLogEntry(collection=views[row.id], role=role) for row, role in rows]
        seen = {row.id for row, _ in rows}
        entries += [LifeLogEntry(collection=views[row.id], role=CollectionRole.PLACE) for row in places if row.id not in seen]
        return LifeLogView(node_id=node_id, entries=entries)


@router.get("/histories/{collection_id}", response_model=HistoryDetail)
async def history(services: ServicesDep, collection_id: Id) -> HistoryDetail:
    async with reader(services) as session:
        row = await session.get(CollectionRow, collection_id)
        if row is None:
            raise NotFoundError("No such history.")
        parent = await session.get(CollectionRow, row.parent_id) if row.parent_id is not None else None
        children = list(
            await session.scalars(select(CollectionRow).where(CollectionRow.parent_id == row.id).order_by(CollectionRow.start_epoch, CollectionRow.id))
        )
        members = list(
            await session.scalars(
                select(CollectionMemberRow)
                .where(CollectionMemberRow.collection_id == row.id)
                .order_by(CollectionMemberRow.since_epoch, CollectionMemberRow.node_id)
            )
        )
        places = list(
            await session.scalars(
                select(CollectionPlaceRow.place_entity_id).where(CollectionPlaceRow.collection_id == row.id).order_by(CollectionPlaceRow.place_entity_id)
            )
        )
        lines = (
            await session.execute(
                select(IncidentRow.id, IncidentRow.epoch, ChronicleRow.text)
                .join(CollectionIncidentRow, CollectionIncidentRow.incident_id == IncidentRow.id)
                .outerjoin(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
                .where(CollectionIncidentRow.collection_id == row.id)
                .order_by(IncidentRow.epoch, IncidentRow.id)
            )
        ).all()
        refs = await node_refs(session, [*(member.node_id for member in members), *places])
        views = await collection_views(session, [row, *([parent] if parent else []), *children])
        by_id = {view.id: view for view in views}
        return HistoryDetail(
            collection=by_id[row.id],
            parent=by_id[parent.id] if parent is not None else None,
            children=[by_id[child.id] for child in children],
            roster=[HistoryMemberView(node=ref(refs, member.node_id), role=member.role, since_epoch=member.since_epoch) for member in members],
            sites=[refs[place] for place in places if place in refs],
            incidents=[IncidentLine(id=incident, epoch=epoch, text=text) for incident, epoch, text in lines],
        )


@router.get("/storyteller/{world_id}", response_model=StorytellerView)
async def storyteller(services: ServicesDep, world_id: Id) -> StorytellerView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        row = await session.get(StorytellerRow, world_id)
        records = list(
            await session.scalars(select(TensionRecordRow).where(TensionRecordRow.world_id == world_id).order_by(TensionRecordRow.epoch, TensionRecordRow.id))
        )
        spotlight = (await node_refs(session, [row.spotlight_entity_id])).get(row.spotlight_entity_id) if row is not None and row.spotlight_entity_id else None
        return StorytellerView(
            world_id=world_id,
            profile=row.profile if row is not None else StorytellerProfile.CYCLIC,
            tension=row.tension if row is not None else 0,
            target=row.target if row is not None else 0,
            band=row.band if row is not None else TensionBand.IN_BAND,
            boost_pct=row.boost_pct if row is not None else 0,
            cycle_offset=row.cycle_offset if row is not None else 0,
            spotlight=spotlight,
            recent_kinds={SpontaneousKind(kind): count for kind, count in (row.recent_kinds or {}).items()} if row is not None else {},
            updated_epoch=row.updated_epoch if row is not None else 0,
            locked=list(row.locked or []) if row is not None else [],
            curve=[
                TensionPoint(epoch=point.epoch, tension=point.tension, target=point.target, boost_pct=point.boost_pct, band=point.band) for point in records
            ],
        )


@router.get("/sites/{entity_id}", response_model=SiteView)
async def site(services: ServicesDep, entity_id: Id) -> SiteView:
    async with reader(services) as session:
        found = await session.get(EntityRow, entity_id)
        if found is None:
            raise NotFoundError("No such site.")
        rooms = list(await session.scalars(select(SiteRoomRow).where(SiteRoomRow.site_entity_id == entity_id).order_by(SiteRoomRow.position, SiteRoomRow.id)))
        room_ids = [room.id for room in rooms]
        contents = (
            list(await session.scalars(select(RoomContentRow).where(RoomContentRow.room_id.in_(room_ids)).order_by(RoomContentRow.id))) if room_ids else []
        )
        holders = list(
            await session.scalars(select(SiteHolderRow).where(SiteHolderRow.site_entity_id == entity_id).order_by(SiteHolderRow.from_epoch, SiteHolderRow.id))
        )
        digs = list(
            await session.scalars(
                select(ExcavationRow).where(ExcavationRow.site_entity_id == entity_id).order_by(ExcavationRow.started_epoch, ExcavationRow.id)
            )
        )
        dig_ids = [dig.id for dig in digs]
        stages = (
            list(await session.scalars(select(ExcavationStageRow).where(ExcavationStageRow.excavation_id.in_(dig_ids)).order_by(ExcavationStageRow.id)))
            if dig_ids
            else []
        )
        features = list(
            await session.scalars(select(BattlefieldFeatureRow).where(BattlefieldFeatureRow.place_entity_id == entity_id).order_by(BattlefieldFeatureRow.id))
        )
        refs = await node_refs(
            session,
            {
                *(content.entity_id for content in contents if content.entity_id is not None),
                *(room.cleared_by_entity_id for room in rooms if room.cleared_by_entity_id is not None),
                *(holder.holder_node_id for holder in holders),
                *(node for dig in digs for node in (dig.leader_entity_id, dig.sponsor_node_id) if node is not None),
                *(stage.find_entity_id for stage in stages if stage.find_entity_id is not None),
            },
        )
        histories = await collection_names(session, [dig.collection_id for dig in digs])
        battles = await battle_names(session, [row.battle_id for row in features])
        layout = await layout_of(await manual_context(session, "site_view"), found)
        return SiteView(
            site_id=entity_id,
            roomed=layout is not None or bool(rooms),
            diggable=await diggable(session, found),
            rooms=[
                RoomView(
                    id=room.id,
                    position=room.position,
                    kind=room.kind,
                    challenge=room.challenge,
                    difficulty=room.difficulty,
                    cleared_epoch=room.cleared_epoch,
                    cleared_by=ref(refs, room.cleared_by_entity_id),
                    locked=list(room.locked or []),
                    contents=[
                        ContentView(id=content.id, kind=content.kind, entity=ref(refs, content.entity_id), strength=content.strength, locked=content.locked)
                        for content in contents
                        if content.room_id == room.id
                    ],
                )
                for room in rooms
            ],
            holders=[
                HolderView(id=holder.id, holder=ref(refs, holder.holder_node_id), from_epoch=holder.from_epoch, to_epoch=holder.to_epoch, how=holder.how)
                for holder in holders
            ],
            digs=[
                DigView(
                    id=dig.id,
                    stage=dig.stage,
                    status=dig.status,
                    progress=dig.progress,
                    leader=ref(refs, dig.leader_entity_id),
                    sponsor=ref(refs, dig.sponsor_node_id),
                    collection_id=dig.collection_id,
                    collection_name=histories.get(dig.collection_id or 0),
                    started_epoch=dig.started_epoch,
                    ended_epoch=dig.ended_epoch,
                    idle_epochs=dig.idle_epochs,
                    note=dig.note,
                    locked=list(dig.locked or []),
                    stages=[
                        DigStageView(
                            id=stage.id,
                            stage=stage.stage,
                            skill=stage.skill,
                            technique=stage.technique,
                            difficulty=stage.difficulty,
                            risk=stage.risk,
                            find=stage.find,
                            find_item=ref(refs, stage.find_entity_id),
                            resolved_epoch=stage.resolved_epoch,
                            locked=list(stage.locked or []),
                        )
                        for stage in stages
                        if stage.excavation_id == dig.id
                    ],
                )
                for dig in digs
            ],
            features=[
                FeatureView(
                    id=row.id,
                    feature=row.feature,
                    strength=row.strength,
                    battle_id=row.battle_id,
                    battle_name=battles.get(row.battle_id or 0),
                    epoch=row.epoch,
                    locked=list(row.locked or []),
                )
                for row in features
            ],
        )
