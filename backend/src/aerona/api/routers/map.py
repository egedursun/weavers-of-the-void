import asyncio

from fastapi import APIRouter, Path, Query
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.geography import geography_lines
from aerona.agents.context.scope import load_scope
from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import Done
from aerona.api.schemas.entities import MapPositionRequest
from aerona.api.schemas.maps import (
    GeographyPreview,
    MapArmy,
    MapConvoy,
    MapFront,
    MapHoly,
    MapLair,
    MapLore,
    MapOccupation,
    MapOutbreak,
    MapPoint,
    MapRelation,
    MapRoad,
    MapTime,
    MapTrade,
    MapView,
    MapWar,
    RegionDeJure,
    RegionDivineRule,
    RegionGround,
    RegionRealm,
    RegionStocks,
    RegionTongue,
    RelationLineKind,
)
from aerona.api.schemas.records import EntitySummary, MapNoteRecord, WorldRecord
from aerona.cartography.generator import generate_map
from aerona.cartography.model import MARKER_TYPES, WorldMap
from aerona.core.errors import NotFoundError
from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agrarian import CentralPlaceRow, LandRingRow, SoilNutrientRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldMapRow, WorldRow
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.culture import ArtworkProfileRow, CastingRow, HolderLevelRow, IdeologyAdherentRow, LanguageStandingRow, LegendProfileRow
from aerona.db.tables.cycles import AsabiyyaRow
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.dominion import RegionDominionRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.economy import TradeFlowRow, TradeRouteProfileRow, TradeRouteRegionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import SpeciesTraitRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.military import ArmyProfileRow, CampaignFrontRow, OccupationRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import PolityTerritoryRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.titles import DeJureLinkRow, TitleProfileRow
from aerona.db.tables.urban import ConvoyRow, DistrictServiceRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agrarian import CentralityRank, LandUseRing, NutrientKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.faith import HoldingKind
from aerona.domain.enums.war import WarStatus
from aerona.domain.models.records import GroundSnapshot
from aerona.engine.cosmos.maps import MAPPED_STATUSES, map_is_stale, map_request, store_world_map, world_entities
from aerona.engine.ecology.niches import NicheKey, niche_of
from aerona.engine.economy.convoys import OPEN
from aerona.engine.economy.routes import LIVE_STATUSES
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat
from aerona.services.container import Services
from aerona.services.images.records import covers_of
from aerona.services.map_lines import region_creators, relation_lines, routed_roads, war_sites
from aerona.services.wiki import (
    event_markers,
    ground_snapshot,
    historical_view,
    map_notes,
    political_map,
    region_dominance,
    road_network,
    settlement_tiers,
    snapshot_epochs,
)

router = APIRouter(tags=["map"])

NO_WORLD = "No such world."
NO_ENTITY = "No such entity."
POSITION_TOOL = "map:position"
POPULATED = (EntityType.PEOPLE, EntityType.SETTLEMENT)

ALIASES = (
    Alias("POST", "/map-notes", "map_note:add"),
    Alias("DELETE", "/map-notes/{note_id}", "map_note:remove", path_fields={"note_id": "note_id"}),
)
RING_ORDER = tuple(LandUseRing)
RANK_ORDER = tuple(CentralityRank)


def stored_map(row: WorldMapRow | None) -> WorldMap | None:
    if row is None:
        return None
    try:
        return WorldMap.model_validate(row.geometry)
    except ValidationError:
        return None


async def geometry(services: Services, world_id: int) -> WorldMap:
    writable = not services.application.discovery.active
    async with reader(services) as session:
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError(NO_WORLD)
        current = None if await map_is_stale(session, world_id) else stored_map(await session.get(WorldMapRow, world_id))
        if current is not None:
            return current
        rules = await world_rules(services, session)
        request = map_request(world, await world_entities(session, world_id))
    if writable:
        async with services.database.write() as session:
            fresh = await session.get(WorldRow, world_id)
            if fresh is None:
                raise NotFoundError(NO_WORLD)
            epoch = (await CosmosRepository(session).require_cosmos()).epoch
            return await store_world_map(session, rules, fresh, epoch)
    return (await asyncio.to_thread(generate_map, request, rules)).world_map


@router.get("/worlds/{world_id}/map", response_model=MapView)
async def read_map(services: ServicesDep, world_id: int = Path(ge=1), epoch: int | None = Query(default=None, ge=1)) -> MapView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError(NO_WORLD)
    shape = await geometry(services, world_id)
    async with reader(services) as session:
        rules = await world_rules(services, session)
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError(NO_WORLD)
        current = (await CosmosRepository(session).require_cosmos()).epoch
        shown = epoch if epoch is not None and epoch < current else current
        entities = list(
            await session.scalars(
                select(EntityRow)
                .where(
                    EntityRow.world_id == world_id, EntityRow.status.in_(MAPPED_STATUSES), EntityRow.entity_type.in_(list(MARKER_TYPES | {EntityType.REGION}))
                )
                .order_by(EntityRow.id)
            )
        )
        population = {entity.id: round(stat(entity, "population") or 0) for entity in entities if entity.entity_type in POPULATED}
        past = await historical_view(session, world_id, shown) if shown != current else None
        if past is not None:
            entities = past.entities
            population = past.population
            political = past.political
        else:
            if shown != current:
                entities = [entity for entity in entities if entity.birth_epoch <= shown and (entity.end_epoch is None or entity.end_epoch > shown)]
            political = await political_map(session, rules, world_id)
        positions = {row.id: (row.map_x, row.map_y) for row in entities if row.map_x is not None and row.map_y is not None}
        roads = await road_network(session, world_id)
        routed = await asyncio.to_thread(routed_roads, shape, roads, positions)
        lines = await relation_lines(session, shape, positions, roads)
        covers = await covers_of(session, [row.id for row in entities])
        return MapView(
            world=WorldRecord.model_validate(world),
            geometry=shape,
            points=[MapPoint(entity=EntitySummary.model_validate(row), x=row.map_x, y=row.map_y, cover=covers.get(row.id)) for row in entities],
            political=political,
            roads=[MapRoad(first=item.road.first, second=item.road.second, kind=item.road.kind, length=item.road.length, path=item.path) for item in routed],
            relations=[
                MapRelation(source=line.source, target=line.target, kind=RelationLineKind(line.kind), description=line.description, path=line.path)
                for line in lines
            ],
            wars=[MapWar.model_validate(site) for site in await war_sites(session, world_id, shown, current)],
            region_creators=region_creators(entities),
            settlements=await settlement_tiers(session, rules, world_id, shown),
            markers=await event_markers(session, world_id),
            dominance=await region_dominance(session, world_id),
            population=population,
            ground=await region_ground(session, world_id, past.ground if past is not None else None),
            stocks=await region_stocks(session, world_id),
            trade=await trade_lines(session, world_id, positions),
            convoys=await convoy_marks(session, world_id, positions),
            outbreaks=await outbreak_lines(session, world_id, positions),
            realms=await region_realms(session, world_id),
            de_jure=await region_de_jure(session, world_id),
            dominion=await region_rulers(session, world_id),
            armies=await army_marks(session, world_id, positions),
            occupations=await occupation_marks(session, world_id),
            fronts=await front_lines(session, world_id, positions),
            holy=await holy_marks(session, world_id, positions),
            lore=await lore_marks(session, world_id, positions, current),
            tongues=await region_tongues(session, world_id),
            lairs=await lair_marks(session, world_id, positions, rules.beasts.raid_reach),
            notes=[MapNoteRecord.model_validate(row) for row in await map_notes(session, world_id)],
            time=MapTime(current=current, shown=shown, snapshots=await snapshot_epochs(session, world_id)),
        )


async def region_realms(session: AsyncSession, world_id: int) -> dict[int, RegionRealm]:
    statement = (
        select(PolityTerritoryRow, EntityRow.name)
        .join(EntityRow, EntityRow.id == PolityTerritoryRow.polity_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    )
    found: dict[int, RegionRealm] = {}
    for row, name in await session.execute(statement):
        current = found.get(row.region_entity_id)
        if current is None or row.control > current.control:
            found[row.region_entity_id] = RegionRealm(polity_id=row.polity_entity_id, name=name, control=row.control)
    return found


async def region_rulers(session: AsyncSession, world_id: int) -> dict[int, RegionDivineRule]:
    statement = (
        select(RegionDominionRow, NodeRow.kind, NodeRow.name)
        .join(NodeRow, NodeRow.id == RegionDominionRow.god_node_id)
        .where(RegionDominionRow.world_id == world_id)
    )
    return {
        row.region_entity_id: RegionDivineRule(god_id=row.god_node_id, kind=kind, name=name, share=row.share, rivals=row.rivals)
        for row, kind, name in await session.execute(statement)
    }


async def top_title(session: AsyncSession, title_id: int) -> TitleProfileRow | None:
    current = await session.get(TitleProfileRow, title_id)
    seen: set[int] = set()
    while current is not None and current.de_jure_liege_entity_id is not None and current.title_entity_id not in seen:
        seen.add(current.title_entity_id)
        upper = await session.get(TitleProfileRow, current.de_jure_liege_entity_id)
        if upper is None:
            break
        current = upper
    return current


async def region_de_jure(session: AsyncSession, world_id: int) -> dict[int, RegionDeJure]:
    realms = await region_realms(session, world_id)
    links = await session.execute(
        select(DeJureLinkRow.member_entity_id, DeJureLinkRow.title_entity_id)
        .join(EntityRow, EntityRow.id == DeJureLinkRow.member_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)
    )
    found: dict[int, RegionDeJure] = {}
    for region_id, title_id in links:
        top = await top_title(session, title_id)
        entity = await session.get(EntityRow, top.title_entity_id) if top is not None else None
        if top is None or entity is None:
            continue
        held = realms.get(region_id)
        found[region_id] = RegionDeJure(
            title_id=top.title_entity_id,
            name=entity.name,
            polity_id=top.polity_entity_id,
            held_by_right=held is not None and held.polity_id == top.polity_entity_id,
        )
    return found


async def army_marks(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapArmy]:
    statement = (
        select(ArmyRow, ArmyProfileRow, EntityRow)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
        .join(EntityRow, EntityRow.id == ArmyRow.entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, ArmyRow.disbanded_epoch.is_(None))
        .order_by(ArmyRow.entity_id)
    )
    found: list[MapArmy] = []
    for army, profile, entity in await session.execute(statement):
        route = [*profile.supply_line] or ([profile.region_entity_id] if profile.region_entity_id is not None else [])
        path = [value for node in route if (point := positions.get(node)) is not None for value in point]
        found.append(
            MapArmy(
                army_id=army.entity_id,
                name=entity.name,
                owner_id=army.owner_entity_id,
                war_id=army.war_id,
                region_id=profile.region_entity_id,
                stance=profile.stance,
                size=round(stat(entity, "size") or 0),
                blockade_id=profile.blockade_entity_id,
                path=path,
            )
        )
    return found


async def occupation_marks(session: AsyncSession, world_id: int) -> dict[int, MapOccupation]:
    statement = (
        select(OccupationRow, EntityRow.name)
        .join(EntityRow, EntityRow.id == OccupationRow.occupier_entity_id)
        .where(EntityRow.world_id == world_id)
        .order_by(OccupationRow.region_entity_id)
    )
    return {
        row.region_entity_id: MapOccupation(occupier_id=row.occupier_entity_id, name=name, control=row.control, resistance=row.resistance)
        for row, name in await session.execute(statement)
    }


async def front_lines(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapFront]:
    statement = (
        select(CampaignFrontRow)
        .join(WarRow, WarRow.id == CampaignFrontRow.war_id)
        .where(WarRow.world_id == world_id, WarRow.status != WarStatus.ENDED)
        .order_by(CampaignFrontRow.id)
    )
    return [
        MapFront(
            war_id=row.war_id,
            first_region_id=row.first_region_id,
            second_region_id=row.second_region_id,
            path=[value for node in (row.first_region_id, row.second_region_id) if (point := positions.get(node)) is not None for value in point],
        )
        for row in await session.scalars(statement)
    ]


async def holy_marks(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapHoly]:
    statement = (
        select(CultHoldingRow, EntityRow.name)
        .join(EntityRow, EntityRow.id == CultHoldingRow.cult_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, CultHoldingRow.kind != HoldingKind.LAND)
        .order_by(CultHoldingRow.cult_entity_id, CultHoldingRow.holding_entity_id)
    )
    found: list[MapHoly] = []
    for row, name in await session.execute(statement):
        point = positions.get(row.holding_entity_id)
        if point is not None:
            found.append(MapHoly(cult_id=row.cult_entity_id, cult=name, holding_id=row.holding_entity_id, kind=row.kind, x=point[0], y=point[1]))
    return found


async def lore_marks(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]], current: int) -> list[MapLore]:
    found: list[MapLore] = []
    haunts = await session.execute(
        select(EntityRow.id, EntityRow.name, EntityRow.location_id, LegendProfileRow.credence)
        .join(LegendProfileRow, LegendProfileRow.legend_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, LegendProfileRow.archetype == LegendArchetype.HAUNTED_PLACE)
    )
    for entity_id, name, place, credence in haunts:
        if place in positions:
            found.append(
                MapLore(
                    kind="haunted", entity_id=entity_id, name=name, place_id=place, x=positions[place][0], y=positions[place][1], detail=f"{credence}% believed"
                )
            )
    works = await session.execute(
        select(EntityRow.id, EntityRow.name, EntityRow.location_id, ArtworkProfileRow.medium)
        .join(ArtworkProfileRow, ArtworkProfileRow.artwork_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    )
    for entity_id, name, place, medium in works:
        if place in positions:
            found.append(MapLore(kind="artwork", entity_id=entity_id, name=name, place_id=place, x=positions[place][0], y=positions[place][1], medium=medium))
    casters = await session.execute(
        select(CastingRow.rite_entity_id, EntityRow.location_id, CastingRow.effect)
        .join(EntityRow, EntityRow.id == CastingRow.caster_entity_id)
        .where(EntityRow.world_id == world_id, CastingRow.epoch >= current - 1)
        .order_by(CastingRow.id)
    )
    names = dict((await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.RITE))).all())
    for rite_id, place, effect in casters:
        if place in positions:
            found.append(
                MapLore(
                    kind="casting",
                    entity_id=rite_id,
                    name=names.get(rite_id, "rite"),
                    place_id=place,
                    x=positions[place][0],
                    y=positions[place][1],
                    detail=effect or None,
                )
            )
    adherents = await session.execute(
        select(
            IdeologyAdherentRow.ideology_entity_id,
            IdeologyAdherentRow.adherent_entity_id,
            IdeologyAdherentRow.strength,
            IdeologyAdherentRow.state,
            EntityRow.name,
        )
        .join(EntityRow, EntityRow.id == IdeologyAdherentRow.ideology_entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(IdeologyAdherentRow.ideology_entity_id, IdeologyAdherentRow.adherent_entity_id)
    )
    for creed_id, place, strength, state, name in adherents:
        if place in positions:
            detail = f"state creed, held {strength}%" if state else f"held {strength}%"
            found.append(MapLore(kind="creed", entity_id=creed_id, name=name, place_id=place, x=positions[place][0], y=positions[place][1], detail=detail))
    learning = await session.execute(
        select(HolderLevelRow.holder_entity_id, func.max(HolderLevelRow.level), func.count(HolderLevelRow.branch))
        .join(EntityRow, EntityRow.id == HolderLevelRow.holder_entity_id)
        .where(EntityRow.world_id == world_id, HolderLevelRow.level >= 1)
        .group_by(HolderLevelRow.holder_entity_id)
    )
    for holder, level, branches in learning:
        if holder in positions:
            found.append(
                MapLore(
                    kind="learning",
                    entity_id=holder,
                    name=f"level {level}",
                    place_id=holder,
                    x=positions[holder][0],
                    y=positions[holder][1],
                    detail=f"{several(branches, 'branch', 'branches')} known, the deepest at level {level}",
                )
            )
    return found


async def region_tongues(session: AsyncSession, world_id: int) -> dict[int, RegionTongue]:
    atlas = await RegionAtlas.load(session)
    speech = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    )
    tally: dict[int, dict[int, int]] = {}
    for speaker, language in speech:
        region = atlas.top_region(speaker)
        if region is not None:
            tally.setdefault(region, {})
            tally[region][language] = tally[region].get(language, 0) + 1
    standings = {row.language_entity_id: row for row in await session.scalars(select(LanguageStandingRow))}
    names = dict(
        (await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.world_id == world_id))).all()
    )
    found: dict[int, RegionTongue] = {}
    for region, counts in tally.items():
        language = max(counts, key=lambda item: (counts[item], standings[item].prestige if item in standings else 0, -item))
        standing = standings.get(language)
        found[region] = RegionTongue(
            language_id=language,
            name=names.get(language, "?"),
            prestige=standing.prestige if standing is not None else 0,
            lingua_franca=standing.lingua_franca if standing is not None else False,
        )
    return found


async def outbreak_lines(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapOutbreak]:
    regions = set(await session.scalars(select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)))
    rows = [row for row in await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)) if row.region_entity_id in regions]
    endemic = [row for row in await session.scalars(select(EndemicDiseaseRow)) if row.region_entity_id in regions]
    sources = {
        row.id: row.region_entity_id
        for row in await session.scalars(select(OutbreakRow).where(OutbreakRow.id.in_([item.source_outbreak_id for item in rows if item.source_outbreak_id])))
    }
    names = dict(
        (
            await session.execute(
                select(EntityRow.id, EntityRow.name).where(
                    EntityRow.id.in_([*(row.disease_entity_id for row in rows), *(row.disease_entity_id for row in endemic)])
                )
            )
        ).all()
    )
    lines: list[MapOutbreak] = []
    for row in rows:
        source = sources.get(row.source_outbreak_id) if row.source_outbreak_id is not None else None
        points = [positions.get(node) for node in ((source, row.region_entity_id) if source is not None else (row.region_entity_id,))]
        path = [value for point in points if point is not None for value in point]
        lines.append(
            MapOutbreak(
                outbreak_id=row.id,
                disease_id=row.disease_entity_id,
                disease=names.get(row.disease_entity_id, ""),
                region_id=row.region_entity_id,
                source_region_id=source,
                status=row.status,
                severity=row.severity,
                dead=row.dead,
                endemic=False,
                path=path,
            )
        )
    for sick in endemic:
        point = positions.get(sick.region_entity_id)
        lines.append(
            MapOutbreak(
                outbreak_id=0,
                disease_id=sick.disease_entity_id,
                disease=names.get(sick.disease_entity_id, ""),
                region_id=sick.region_entity_id,
                source_region_id=None,
                status=OutbreakStatus.WANING,
                severity=sick.load,
                dead=0,
                endemic=True,
                path=list(point) if point is not None else [],
            )
        )
    return lines


async def trade_lines(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapTrade]:
    statement = (
        select(TradeRouteProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == TradeRouteProfileRow.route_entity_id)
        .where(EntityRow.world_id == world_id, TradeRouteProfileRow.status.in_(list(LIVE_STATUSES)))
        .order_by(TradeRouteProfileRow.route_entity_id)
    )
    found = list(await session.execute(statement))
    if not found:
        return []
    ids = [profile.route_entity_id for profile, _ in found]
    steps: dict[int, list[tuple[int, int]]] = {}
    for step in await session.scalars(select(TradeRouteRegionRow).where(TradeRouteRegionRow.route_entity_id.in_(ids))):
        steps.setdefault(step.route_entity_id, []).append((step.position, step.region_entity_id))
    latest = await session.scalar(select(func.max(TradeFlowRow.epoch)))
    volumes: dict[int, int] = {}
    if latest is not None:
        for route_id, volume in await session.execute(select(TradeFlowRow.route_entity_id, TradeFlowRow.volume).where(TradeFlowRow.epoch == latest)):
            volumes[route_id] = volumes.get(route_id, 0) + volume
    lines: list[MapTrade] = []
    for profile, entity in found:
        middle = [region for _, region in sorted(steps.get(profile.route_entity_id, []))][1:-1]
        points = [positions.get(node) for node in (profile.first_market_id, *middle, profile.second_market_id)]
        path = [value for point in points if point is not None for value in point]
        if len(path) < 4:
            continue
        lines.append(
            MapTrade(
                route_id=entity.id,
                name=entity.name,
                first=profile.first_market_id,
                second=profile.second_market_id,
                mode=profile.mode,
                status=profile.status,
                volume=volumes.get(entity.id, 0),
                capacity=stat(entity, "capacity") or 0,
                path=path,
            )
        )
    return lines


STOCK_KEYS = {EntityType.PEOPLE: "population", EntityType.SETTLEMENT: "population", EntityType.CULT: "followers", EntityType.ARMY: "soldiers"}


async def region_ground(session: AsyncSession, world_id: int, past: dict[int, GroundSnapshot] | None = None) -> dict[int, RegionGround]:
    current = await ground_snapshot(session, world_id)
    shown = {**current, **past} if past else current
    return {region_id: RegionGround.model_validate(item.model_dump()) for region_id, item in shown.items()}


async def region_stocks(session: AsyncSession, world_id: int) -> dict[int, RegionStocks]:
    atlas = await RegionAtlas.load(session)
    totals: dict[int, dict[str, int]] = {}
    for entity in await canon(session, list(STOCK_KEYS), world_id):
        region = atlas.top_region(entity.id)
        if region is None:
            continue
        key = STOCK_KEYS[entity.entity_type]
        value = stat(entity, "size" if key == "soldiers" else key) or 0
        bucket = totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0})
        bucket[key] += value
    regions = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)
    for region, total in await session.execute(
        select(SpeciesRangeRow.region_entity_id, func.sum(SpeciesRangeRow.abundance))
        .where(SpeciesRangeRow.region_entity_id.in_(regions))
        .group_by(SpeciesRangeRow.region_entity_id)
    ):
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0})["wildlife"] = int(total or 0)
    for region, values in (await urban_by_region(session, world_id, atlas)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0}).update(values)
    for region, count in (await niches_by_region(session, world_id)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0})["niches"] = count
    for region, values in (await solidarity_by_region(session, world_id, atlas)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0}).update(values)
    for region, values in (await agrarian_by_region(session, world_id, atlas)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0}).update(values)
    for region, count in (await networks_by_region(session, world_id, atlas)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0})["networks"] = count
    for region, count in (await hidden_by_region(session, world_id, atlas)).items():
        totals.setdefault(region, {"population": 0, "followers": 0, "soldiers": 0})["hidden"] = count
    return {region: RegionStocks(**values) for region, values in totals.items()}


async def hidden_by_region(session: AsyncSession, world_id: int, atlas: RegionAtlas) -> dict[int, int]:
    found: dict[int, int] = {}
    subjects = (
        select(HiddenTruthRow.subject_node_id)
        .join(EntityRow, EntityRow.id == HiddenTruthRow.subject_node_id)
        .where(EntityRow.world_id == world_id, HiddenTruthRow.revealed.is_(False))
    )
    for subject in await session.scalars(subjects):
        region = atlas.top_region(subject)
        if region is not None:
            found[region] = found.get(region, 0) + 1
    return found


async def networks_by_region(session: AsyncSession, world_id: int, atlas: RegionAtlas) -> dict[int, int]:
    reached: dict[int, set[int]] = {}
    members = (
        select(NetworkNodeRow.network_entity_id, EntityRow.id)
        .join(EntityRow, EntityRow.id == NetworkNodeRow.member_node_id)
        .where(EntityRow.world_id == world_id)
    )
    anchors = (
        select(NetworkProfileRow.network_entity_id, EntityRow.id)
        .join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id)
        .where(EntityRow.world_id == world_id)
    )
    for network, place in [*(await session.execute(members)).all(), *(await session.execute(anchors)).all()]:
        region = atlas.top_region(place)
        if region is not None:
            reached.setdefault(region, set()).add(network)
    return {region: len(networks) for region, networks in reached.items()}


async def urban_by_region(session: AsyncSession, world_id: int, atlas: RegionAtlas) -> dict[int, dict[str, int]]:
    towns = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    wanted: dict[int, list[int]] = {}
    covered: dict[int, list[int]] = {}
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id.in_(towns))))
    service = {
        district_id: coverage
        for district_id, coverage in await session.execute(
            select(DistrictServiceRow.district_id, func.avg(DistrictServiceRow.coverage))
            .where(DistrictServiceRow.district_id.in_([row.id for row in districts]))
            .group_by(DistrictServiceRow.district_id)
        )
    }
    for district in districts:
        region = atlas.top_region(district.settlement_entity_id)
        if region is not None:
            wanted.setdefault(region, []).append(district.desirability)
            covered.setdefault(region, []).append(round(float(service.get(district.id) or 0)))
    return {
        region: {"desirability": round(sum(values) / len(values)), "coverage": round(sum(covered[region]) / len(covered[region]))}
        for region, values in wanted.items()
    }


async def agrarian_by_region(session: AsyncSession, world_id: int, atlas: RegionAtlas) -> dict[int, dict[str, int]]:
    found: dict[int, dict[str, int]] = {}
    rings = await session.execute(
        select(LandRingRow.region_entity_id, LandRingRow.ring)
        .join(EntityRow, EntityRow.id == LandRingRow.region_entity_id)
        .where(EntityRow.world_id == world_id)
    )
    for region, ring in rings.all():
        found.setdefault(region, {})["ring"] = RING_ORDER.index(ring) + 1
    places = await session.execute(
        select(CentralPlaceRow.settlement_entity_id, CentralPlaceRow.rank)
        .join(EntityRow, EntityRow.id == CentralPlaceRow.settlement_entity_id)
        .where(EntityRow.world_id == world_id)
    )
    for settlement, rank in places.all():
        home = atlas.top_region(settlement)
        if home is not None:
            bucket = found.setdefault(home, {})
            bucket["market"] = max(bucket.get("market", 0), RANK_ORDER.index(rank) + 1)
    soils = await session.execute(
        select(SoilNutrientRow.region_entity_id, SoilNutrientRow.nutrient, SoilNutrientRow.stock)
        .join(EntityRow, EntityRow.id == SoilNutrientRow.region_entity_id)
        .where(EntityRow.world_id == world_id)
    )
    body: dict[int, list[int]] = {}
    for region, nutrient, stock in soils.all():
        if nutrient is NutrientKind.SALINITY:
            found.setdefault(region, {})["salt"] = stock
        else:
            body.setdefault(region, []).append(stock)
    for region, stocks in body.items():
        found.setdefault(region, {})["soil"] = max(1, round(sum(stocks) / len(stocks)))
    return found


async def solidarity_by_region(session: AsyncSession, world_id: int, atlas: RegionAtlas) -> dict[int, dict[str, int]]:
    found: dict[int, dict[str, int]] = {}
    for row, holder in await session.execute(
        select(AsabiyyaRow, EntityRow).join(EntityRow, EntityRow.id == AsabiyyaRow.holder_entity_id).where(EntityRow.world_id == world_id)
    ):
        for home in await homes_of(session, holder):
            region = atlas.top_region(home)
            if region is None:
                continue
            bucket = found.setdefault(region, {"solidarity": 0, "frontier": 0})
            bucket["solidarity"] = max(bucket["solidarity"], row.value)
            bucket["frontier"] = max(bucket["frontier"], row.frontier)
    return found


async def niches_by_region(session: AsyncSession, world_id: int) -> dict[int, int]:
    regions = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION)
    profiles = {row.species_entity_id: row for row in await session.scalars(select(SpeciesProfileRow))}
    sizes = {
        (row.species_entity_id, row.region_entity_id): row
        for row in await session.scalars(
            select(SpeciesTraitRow).where(SpeciesTraitRow.trait == EvolvedTrait.SIZE, SpeciesTraitRow.region_entity_id.in_(regions))
        )
    }
    found: dict[int, set[NicheKey]] = {}
    for row in await session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id.in_(regions), SpeciesRangeRow.abundance > 0)):
        profile = profiles.get(row.species_entity_id)
        if profile is not None:
            found.setdefault(row.region_entity_id, set()).add(niche_of(profile, sizes.get((row.species_entity_id, row.region_entity_id))))
    return {region: len(keys) for region, keys in found.items()}


async def convoy_marks(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]]) -> list[MapConvoy]:
    routes = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.TRADE_ROUTE)
    rows = await session.execute(
        select(ConvoyRow, TradeRouteProfileRow)
        .join(TradeRouteProfileRow, TradeRouteProfileRow.route_entity_id == ConvoyRow.route_entity_id)
        .where(ConvoyRow.route_entity_id.in_(routes), ConvoyRow.status.in_(list(OPEN)))
        .order_by(ConvoyRow.id)
    )
    pairs = list(rows)
    owners = dict(
        (
            await session.execute(
                select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_([row.owner_entity_id for row, _ in pairs if row.owner_entity_id]))
            )
        ).all()
    )
    found: list[MapConvoy] = []
    for row, profile in pairs:
        first, second = positions.get(profile.first_market_id), positions.get(profile.second_market_id)
        if first is None or second is None:
            continue
        found.append(
            MapConvoy(
                convoy_id=row.id,
                route_id=row.route_entity_id,
                owner=owners.get(row.owner_entity_id, "") if row.owner_entity_id is not None else "",
                status=row.status,
                guards=row.guards,
                path=[*first, *second],
            )
        )
    return found


async def lair_marks(session: AsyncSession, world_id: int, positions: dict[int, tuple[float, float]], reach: int) -> list[MapLair]:
    rows = await session.execute(
        select(EntityRow, BeastProfileRow)
        .join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found: list[MapLair] = []
    for beast, row in rows:
        point = positions.get(row.lair_place_id or 0) or positions.get(beast.location_id or 0) or positions.get(beast.id)
        if point is not None:
            found.append(MapLair(beast_id=beast.id, name=beast.name, x=point[0], y=point[1], terror=stat(beast, "terror") or 0, temper=row.temper, reach=reach))
    return found


@router.get("/worlds/{world_id}/geography", response_model=GeographyPreview)
async def geography_preview(services: ServicesDep, world_id: int = Path(ge=1)) -> GeographyPreview:
    await geometry(services, world_id)
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError(NO_WORLD)
        scope = await load_scope(session, await world_rules(services, session))
        return GeographyPreview(world_id=world_id, text=await geography_lines(scope, world_id))


@router.get("/map-notes", response_model=list[MapNoteRecord])
async def list_map_notes(services: ServicesDep, world_id: int | None = Query(default=None, ge=1)) -> list[MapNoteRecord]:
    async with reader(services) as session:
        return [MapNoteRecord.model_validate(row) for row in await map_notes(session, world_id)]


@router.put("/entities/{entity_id}/map-position", response_model=Done)
async def set_map_position(request: MapPositionRequest, services: ServicesDep, entity_id: int = Path(ge=1)) -> Done:
    async with (
        services.database.write() as session,
        services.application.ledger.creator_action(session, POSITION_TOOL, ActionKind.EDIT_RECORD, {"entity_id": entity_id}),
    ):
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError(NO_ENTITY)
        entity.map_x = round(request.x)
        entity.map_y = round(request.y)
        await session.flush()
    return Done()


mount_all(router, ALIASES, tag="map")
