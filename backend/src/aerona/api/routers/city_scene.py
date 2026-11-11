import math
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.city_scene import (
    CityBuildingView,
    CityDistrictView,
    CitySceneView,
    DwellingTypeView,
    LandPlaceView,
    LandResourceView,
    LandSceneView,
    LandTileView,
    LandWorkView,
    ServiceShare,
    StructureTypesView,
    StructureTypeView,
    TypeInstanceView,
    ZoneShare,
)
from aerona.api.views.common import node_refs
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.urban import AMENITIES, NUISANCES, SERVICE_OF
from aerona.catalog.zones import CIVIC_SERVICE_OF, ZONE_OF_DISTRICT, ZONE_OF_STRUCTURE
from aerona.core.errors import NotFoundError
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import DistrictServiceRow, TurfRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import DistrictKind, SizeTier, WaterSupply
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import HousingLevel, LandCover, LandGround, Morphology, ZoneKind
from aerona.engine.primitives.stats import stat_or
from aerona.engine.urban.cityscape import DIGGINGS, HOUSE_SLOTS, homes_of, land_tiles, pick_tile, provisional, resource_prefer, slots_of
from aerona.engine.urban.coverage import home_of, people_of_districts
from aerona.engine.urban.layout import CENTRE, CityLayout, Hex, water_side
from aerona.engine.urban.planning import coastal

router = APIRouter(tags=["city"])
NodeId = Annotated[int, Path(ge=1)]


def home_scale(layout: CityLayout, slots: dict[int, tuple[Hex, int]], districts: list[DistrictRow], dwellings: dict[int, int], shelters: int) -> int:
    built = {cell for cell, _ in slots.values()}
    room = {district.id: sum(1 for cell in layout.footprints.get(district.id, []) if cell not in built) * HOUSE_SLOTS for district in districts}
    slums = sum(room[district.id] for district in districts if district.kind is DistrictKind.SLUMS)
    needs = [math.ceil(dwellings[district.id] / room[district.id]) for district in districts if room[district.id] > 0 and dwellings[district.id] > 0]
    if shelters and slums:
        needs.append(math.ceil((shelters + sum(dwellings[district.id] for district in districts if district.kind is DistrictKind.SLUMS)) / slums))
    return max(1, *needs) if needs else 1


def home_id(profile: StructureProfileRow, districts: list[DistrictRow]) -> int | None:
    home = home_of(profile, districts)
    return home.id if home is not None else None


async def town_or_fail(session: AsyncSession, settlement_id: int) -> EntityRow:
    town = await session.get(EntityRow, settlement_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT:
        raise NotFoundError("No such settlement.")
    return town


@router.get("/city/{settlement_id}", response_model=CitySceneView)
async def city_scene(services: ServicesDep, settlement_id: NodeId) -> CitySceneView:
    async with reader(services) as session:
        town = await town_or_fail(session, settlement_id)
        rules = await world_rules(services, session)
        profile = await session.get(SettlementProfileRow, town.id)
        infrastructure = await session.get(SettlementInfrastructureRow, town.id)
        walls = infrastructure.walls_level if infrastructure is not None else 0
        morphology = profile.morphology if profile is not None else Morphology.ORGANIC
        districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)))
        layout = provisional(rules, districts, morphology, walls, town.id)
        population = round(stat_or(town, "population", 0))
        people = people_of_districts(rules, population, districts)
        coverage: dict[int, list[ServiceShare]] = defaultdict(list)
        for row in await session.scalars(
            select(DistrictServiceRow).where(DistrictServiceRow.district_id.in_([d.id for d in districts])).order_by(DistrictServiceRow.service)
        ):
            coverage[row.district_id].append(ServiceShare(service=row.service, coverage=row.coverage))
        turf: dict[int, int] = defaultdict(int)
        for held_turf in await session.scalars(select(TurfRow).where(TurfRow.district_id.in_([d.id for d in districts]))):
            turf[held_turf.district_id] = max(turf[held_turf.district_id], held_turf.strength)
        buildings = list(await session.scalars(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == town.id)))
        refs = await node_refs(session, [town.id, *(row.structure_entity_id for row in buildings)])
        buildings = [row for row in buildings if row.structure_entity_id in refs]
        slots = slots_of(layout, buildings, districts)
        household = rules.city_plan.household
        dwellings = {district.id: homes_of(people.get(district.id, 0), household) for district in districts}
        homeless = profile.homeless if profile is not None else 0
        shelters = math.ceil(homeless / household)
        scale = home_scale(layout, slots, districts, dwellings, shelters)
        zones: dict[ZoneKind, ZoneShare] = {zone: ZoneShare(zone=zone, districts=0, cells=0, buildings=0) for zone in ZoneKind}
        for district in districts:
            share = zones[ZONE_OF_DISTRICT[district.kind]]
            share.districts += 1
            share.cells += len(layout.footprints.get(district.id, []))
        for building in buildings:
            zones[ZONE_OF_STRUCTURE[building.kind]].buildings += 1
        return CitySceneView(
            town=refs[town.id],
            morphology=morphology,
            tier=profile.size_tier if profile is not None else SizeTier.HAMLET,
            population=population,
            homeless=homeless,
            shelters=shelters,
            walls_level=walls,
            walls_radius=layout.walls_radius,
            roads=infrastructure.roads if infrastructure is not None else 0,
            water=infrastructure.water if infrastructure is not None else WaterSupply.NONE,
            water_side=water_side(town.id, coastal(districts)),
            scale=scale,
            districts=[
                CityDistrictView(
                    id=district.id,
                    kind=district.kind,
                    zone=ZONE_OF_DISTRICT[district.kind],
                    level=district.level,
                    housing=district.housing,
                    condition=district.condition,
                    desirability=district.desirability,
                    land_value=district.land_value,
                    q=layout.seeds.get(district.id, CENTRE)[0],
                    r=layout.seeds.get(district.id, CENTRE)[1],
                    cells=[list(cell) for cell in layout.footprints.get(district.id, [])],
                    residents=round(people.get(district.id, 0)),
                    dwellings=dwellings[district.id],
                    services=coverage[district.id],
                    turf=turf[district.id],
                    locked=list(district.locked),
                )
                for district in districts
            ],
            buildings=[
                CityBuildingView(
                    node=refs[row.structure_entity_id],
                    kind=row.kind,
                    zone=ZONE_OF_STRUCTURE[row.kind],
                    civic=CIVIC_SERVICE_OF.get(row.kind),
                    service=SERVICE_OF.get(row.kind),
                    district_id=row.district_id,
                    home_district_id=row.district_id if row.district_id is not None else home_id(row, districts),
                    q=slots[row.structure_entity_id][0][0],
                    r=slots[row.structure_entity_id][0][1],
                    slot=slots[row.structure_entity_id][1],
                    level=row.level,
                    condition=row.condition,
                    state=row.construction_state,
                    progress=row.progress,
                    staff_pct=row.staff_pct,
                )
                for row in sorted(buildings, key=lambda item: item.structure_entity_id)
            ],
            zones=[zones[zone] for zone in ZoneKind],
        )


@router.get("/land/{region_id}", response_model=LandSceneView)
async def land_scene(services: ServicesDep, region_id: NodeId) -> LandSceneView:
    async with reader(services) as session:
        region = await session.get(EntityRow, region_id)
        land = await session.get(RegionEnvironmentRow, region_id)
        if region is None or region.entity_type is not EntityType.REGION or land is None:
            raise NotFoundError("No such land.")
        tiles = land_tiles(land, region.id)
        local = list(
            await session.scalars(select(EntityRow).where(EntityRow.location_id == region.id, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))
        )
        refs = await node_refs(session, [region.id, *(row.id for row in local)])
        taken: set[Hex] = set()
        towns = [
            LandPlaceView(node=refs[row.id], q=cell[0], r=cell[1], detail=str(round(stat_or(row, "population", 0))), kind=None, sacred=False)
            for row in local
            if row.entity_type is EntityType.SETTLEMENT and row.id in refs
            for cell in [pick_tile(tiles, taken, (LandCover.BUILT,), (LandGround.LOWLAND, LandGround.SHORE))]
        ]
        kinds = {
            row.entity_id: row.kind for row in await session.scalars(select(PlaceProfileRow).where(PlaceProfileRow.entity_id.in_([row.id for row in local])))
        }
        sites = {
            row.place_entity_id: f"{row.kind.value} · {row.school.value}"
            for row in await session.scalars(select(MagicSiteRow).where(MagicSiteRow.place_entity_id.in_([row.id for row in local])))
        }
        places = [
            LandPlaceView(
                node=refs[row.id],
                q=cell[0],
                r=cell[1],
                detail=sites.get(row.id) or row.subtype or (kind.value.replace("_", " ") if (kind := kinds.get(row.id)) is not None else "place"),
                kind=kinds.get(row.id),
                sacred=row.id in sites,
            )
            for row in local
            if row.entity_type is EntityType.PLACE and row.id in refs
            for cell in [pick_tile(tiles, taken, (LandCover.OPEN, LandCover.FOREST))]
        ]
        works_rows = list(
            await session.scalars(
                select(StructureProfileRow).where(StructureProfileRow.host_entity_id == region.id).order_by(StructureProfileRow.structure_entity_id)
            )
        )
        work_refs = await node_refs(session, [row.structure_entity_id for row in works_rows])
        works = [
            LandWorkView(
                node=work_refs[row.structure_entity_id],
                kind=row.kind,
                state=row.construction_state,
                level=row.level,
                condition=row.condition,
                progress=row.progress,
                q=cell[0],
                r=cell[1],
            )
            for row in works_rows
            if row.structure_entity_id in work_refs
            for cell in [pick_tile(tiles, taken, (LandCover.MINED,) if row.kind in DIGGINGS else (LandCover.OPEN, LandCover.CLEARED))]
        ]
        profiles = {
            row.resource_entity_id: row
            for row in await session.scalars(select(ResourceProfileRow).where(ResourceProfileRow.resource_entity_id.in_([row.id for row in local])))
        }
        resources = []
        for row in local:
            found = profiles.get(row.id)
            if row.entity_type is not EntityType.RESOURCE or found is None or row.id not in refs:
                continue
            prefer, grounds = resource_prefer(found.commodity)
            cell = pick_tile(tiles, taken, prefer, grounds)
            resources.append(
                LandResourceView(
                    node=refs[row.id],
                    commodity=found.commodity,
                    richness=found.richness,
                    reserve=found.reserve,
                    initial_reserve=found.initial_reserve,
                    q=cell[0],
                    r=cell[1],
                )
            )
        return LandSceneView(
            region=refs[region.id],
            terrain=land.dominant_terrain,
            elevation=land.elevation_mean,
            roughness=land.roughness,
            moisture=land.moisture,
            forest_cover=land.forest_cover,
            farmed=land.farmed,
            grazed=land.grazed,
            wetland=land.wetland,
            cleared=land.cleared,
            mined=land.mined,
            built=land.built,
            soil_fertility=land.soil_fertility,
            magic_density=land.magic_density,
            river=land.river_class,
            coast=land.coast_kind,
            temperature=land.temperature_band,
            tiles=[LandTileView(q=tile.q, r=tile.r, ground=tile.ground, cover=tile.cover, river=tile.river) for tile in tiles],
            settlements=towns,
            places=places,
            works=works,
            resources=resources,
        )


@router.get("/structure-types/{world_id}", response_model=StructureTypesView)
async def structure_types(services: ServicesDep, world_id: NodeId) -> StructureTypesView:
    async with reader(services) as session:
        rows = list(
            await session.execute(
                select(StructureProfileRow, EntityRow)
                .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
                .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
                .order_by(StructureProfileRow.kind, EntityRow.id)
            )
        )
        refs = await node_refs(session, [item for profile, entity in rows for item in (entity.id, profile.host_entity_id) if item is not None])
        grouped: dict[StructureKind, list[TypeInstanceView]] = defaultdict(list)
        for profile, entity in rows:
            if entity.id in refs:
                grouped[profile.kind].append(
                    TypeInstanceView(
                        node=refs[entity.id],
                        town=refs.get(profile.host_entity_id) if profile.host_entity_id is not None else None,
                        state=profile.construction_state,
                        level=profile.level,
                    )
                )
        types = []
        for kind in StructureKind:
            spec = STRUCTURES.get(kind)
            types.append(
                StructureTypeView(
                    kind=kind,
                    label=spec.label if spec is not None else kind.value.replace("_", " ").capitalize(),
                    zone=ZONE_OF_STRUCTURE[kind],
                    group=spec.group if spec is not None else None,
                    civic=CIVIC_SERVICE_OF.get(kind),
                    service=SERVICE_OF.get(kind),
                    amenity=kind in AMENITIES,
                    nuisance=kind in NUISANCES,
                    staff=spec.staff if spec is not None else None,
                    tier=spec.min_tier if spec is not None else None,
                    upkeep=spec.upkeep if spec is not None else None,
                    instances=grouped.get(kind, []),
                )
            )
        towns = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.SETTLEMENT)
        districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id.in_(towns))))
        homes: dict[str, list[int]] = defaultdict(list)
        towns_of: dict[str, set[int]] = defaultdict(set)
        population = {row.id: round(stat_or(row, "population", 0)) for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(towns)))}
        rules = await world_rules(services, session)
        by_town: dict[int, list[DistrictRow]] = defaultdict(list)
        for district in districts:
            by_town[district.settlement_entity_id].append(district)
        for town_id, items in by_town.items():
            people = people_of_districts(rules, population.get(town_id, 0), items)
            for district in items:
                homes[district.housing.value].append(homes_of(people.get(district.id, 0), rules.city_plan.household))
                towns_of[district.housing.value].add(town_id)
        town_refs = await node_refs(session, sorted(by_town))
        dwellings = [
            DwellingTypeView(
                housing=level,
                districts=len(homes[level.value]),
                dwellings=sum(homes[level.value]),
                towns=[town_refs[town] for town in sorted(towns_of[level.value]) if town in town_refs],
            )
            for level in HousingLevel
        ]
        return StructureTypesView(world_id=world_id, structures=types, dwellings=dwellings)
