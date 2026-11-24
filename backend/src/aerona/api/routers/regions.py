from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.regions import (
    BeneathView,
    DeepPassageView,
    DepthStratumView,
    HazardExposure,
    MapKnowledgeView,
    RealmChoice,
    RegionDangerView,
    RegionHazardView,
    RegionMemoryView,
    RegionTerrainView,
    RiverNeighbour,
    RockLayerView,
)
from aerona.catalog.dangers import DANGERS, HAZARDS
from aerona.catalog.land_memory import LAND_MEMORIES
from aerona.catalog.rocks import ROCKS
from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionHazardRow, RegionMemoryRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.geology import UndergroundStratum
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.region import DangerHarm
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.book import realm_of
from aerona.engine.environment.columns import carvable, columns_by_region, quarry_grade, stratum_depth
from aerona.engine.environment.dangers import reaches, row_weight, total, weighted
from aerona.engine.environment.hazards import exposed
from aerona.engine.environment.knowledge import reveals
from aerona.engine.environment.memory import darkness, darkness_of, fades, holiness, holiness_of
from aerona.engine.environment.perils import haunt_factor
from aerona.engine.primitives.deep import passage_kind
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up

router = APIRouter(tags=["environment"])


@router.get("/regions/{region_id}/terrain", response_model=RegionTerrainView)
async def region_terrain(services: ServicesDep, region_id: int = Path(ge=1)) -> RegionTerrainView:
    rules = services.rules.current
    async with reader(services) as session:
        ground = await session.get(RegionEnvironmentRow, region_id)
        region = await session.get(EntityRow, region_id)
        if ground is None or region is None:
            raise NotFoundError("This region has not been surveyed yet.")
        dangers = list(
            await session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id).order_by(RegionDangerRow.strength.desc()))
        )
        memories = list(
            await session.scalars(
                select(RegionMemoryRow).where(RegionMemoryRow.region_entity_id == region_id).order_by(RegionMemoryRow.epoch.desc(), RegionMemoryRow.id)
            )
        )
        knowledge = list(await session.scalars(select(PolityMapKnowledgeRow).where(PolityMapKnowledgeRow.region_entity_id == region_id)))
        realms = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == ground.world_id)
                .order_by(EntityRow.name)
            )
        )
        named = {row.source_node_id for row in dangers if row.source_node_id is not None} | {row.polity_entity_id for row in knowledge}
        names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(named))))}
        hazards = list(
            await session.scalars(
                select(RegionHazardRow).where(RegionHazardRow.region_entity_id == region_id).order_by(RegionHazardRow.epoch.desc(), RegionHazardRow.id.desc())
            )
        )
        atlas = await RegionAtlas.load(session)
        neighbour_ids = atlas.neighbour_regions(region_id)
        neighbours = {
            row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(neighbour_ids)))
        }
        neighbour_names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(neighbour_ids)).order_by(EntityRow.name))}
        haunting = await haunt_factor(session, rules, region_id)
    return RegionTerrainView(
        region_id=region.id,
        world_id=ground.world_id,
        danger=total(rules, dangers),
        harms={harm: weighted(rules, dangers, harm) for harm in DangerHarm},
        dangers=[
            RegionDangerView(
                id=row.id,
                source=row.source,
                label=DANGERS[row.source].label,
                strength=row.strength,
                origin=row.origin,
                held=row.held,
                source_node_id=row.source_node_id,
                source_node_name=names.get(row.source_node_id or 0),
                son_id=row.son_id,
                since_epoch=row.since_epoch,
                harms={harm: round_half_up(row.strength * row_weight(rules, row, harm) / PERCENT) for harm in DangerHarm},
                targets=[DangerHarm(target) for target in row.harmed],
                reachable=reaches(rules, row.source),
            )
            for row in dangers
        ],
        sacredness=ground.sacredness,
        sacredness_held="sacredness" in ground.locked,
        darkness=darkness(rules, memories),
        holiness=holiness(rules, memories),
        haunting_pct=round_half_up(haunting * PERCENT),
        draws_pilgrims=ground.sacredness >= rules.terrain.pilgrim_sacred_min,
        pilgrim_sacred_min=rules.terrain.pilgrim_sacred_min,
        memories=[
            RegionMemoryView(
                id=row.id,
                kind=row.kind,
                label=LAND_MEMORIES[row.kind].label,
                magnitude=row.magnitude,
                epoch=row.epoch,
                title=row.title,
                origin=row.origin,
                held=row.held,
                darkness=darkness_of(rules, row.kind),
                holiness=holiness_of(rules, row.kind),
                fades=fades(rules, row.kind),
                subject_id=row.subject_node_id,
                incident_id=row.incident_id,
            )
            for row in memories
        ],
        knowledge=[
            MapKnowledgeView(
                polity_id=row.polity_entity_id,
                polity_name=names.get(row.polity_entity_id, ""),
                level=row.level,
                held=row.held,
                unmapped=row.level < rules.terrain.unmapped_below,
                **reveals(rules, row.level),
            )
            for row in sorted(knowledge, key=lambda item: (-item.level, item.polity_entity_id))
        ],
        realms=[RealmChoice(id=row.id, name=row.name) for row in realms],
        unmapped_below=rules.terrain.unmapped_below,
        hazards=[
            RegionHazardView(
                id=row.id,
                hazard=row.hazard,
                label=HAZARDS[row.hazard].label,
                epoch=row.epoch,
                year=row.year,
                season_name=row.season_name,
                deaths=row.deaths,
                injured=row.injured,
                soldiers_lost=row.soldiers_lost,
            )
            for row in hazards
        ],
        exposure=[
            HazardExposure(hazard=hazard, label=spec.label, season=spec.season) for hazard, spec in HAZARDS.items() if exposed(rules, hazard, spec, ground)
        ],
        river_class=ground.river_class,
        river_neighbours=[
            RiverNeighbour(id=item, name=name, river_class=neighbours[item].river_class if item in neighbours else None)
            for item, name in neighbour_names.items()
        ],
    )


@router.get("/regions/{region_id}/beneath", response_model=BeneathView)
async def region_beneath(services: ServicesDep, region_id: int = Path(ge=1)) -> BeneathView:
    rules = services.rules.current
    async with reader(services) as session:
        ground = await session.get(RegionEnvironmentRow, region_id)
        if ground is None:
            raise NotFoundError("No such region.")
        rows = (await columns_by_region(session, [region_id])).get(region_id, [])
        strata = list(await session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region_id).order_by(RegionStratumRow.id)))
        below = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.location_id == region_id, EntityRow.stratum.is_not(None), EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        passages = list(
            await session.scalars(
                select(DeepPassageRow)
                .where(or_(DeepPassageRow.first_region_entity_id == region_id, DeepPassageRow.second_region_entity_id == region_id))
                .order_by(DeepPassageRow.id)
            )
        )
        named = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(deep_refs(strata, passages, below))))}
        holders = {stratum: await holder_below(session, below, stratum) for stratum in {row.stratum for row in strata}}
    tops = [sum(row.thickness for row in rows[:index]) for index in range(len(rows))]
    return BeneathView(
        region_id=region_id,
        mined_depth=ground.mined * rules.rocks.depth_per_mined,
        quarry_grade=quarry_grade(rows),
        carvable=carvable(rules, rows),
        layers=[
            RockLayerView(
                id=row.id,
                depth_order=row.depth_order,
                rock=row.rock,
                thickness=row.thickness,
                top=top,
                veins=row.veins,
                reached_epoch=row.reached_epoch,
                hardness=ROCKS[row.rock].hardness(rules),
                porosity=ROCKS[row.rock].porosity(rules),
                solubility=ROCKS[row.rock].solubility(rules),
                workability=ROCKS[row.rock].workability(rules),
                grade=ROCKS[row.rock].grade,
                locked=row.locked,
            )
            for row, top in zip(rows, tops, strict=True)
        ],
        strata=[
            DepthStratumView(
                id=row.id,
                stratum=row.stratum,
                depth=stratum_depth(rules, rows, row.stratum),
                volume=row.volume,
                pressure=row.pressure,
                reached_epoch=row.reached_epoch,
                breached_epoch=row.breached_epoch,
                tapped_epoch=row.tapped_epoch,
                name=row.name,
                terrain=row.terrain,
                extent=row.extent,
                light=row.light,
                realm=ref(named, row.realm_entity_id),
                holder=ref(named, holders.get(row.stratum)),
                dwellers=[NodeRef(id=entity.id, kind=NodeKind.ENTITY, name=entity.name) for entity in below if entity.stratum is row.stratum],
                dwellable=STRATA[row.stratum].dwellable,
                locked=row.locked,
            )
            for row in sorted(strata, key=lambda item: (stratum_depth(rules, rows, item.stratum), item.id))
        ],
        passages=[passage_view(passage, region_id, named) for passage in passages],
    )


def ref(named: dict[int, str], node_id: int | None) -> NodeRef | None:
    return NodeRef(id=node_id, kind=NodeKind.ENTITY, name=named.get(node_id, "")) if node_id is not None and node_id in named else None


def deep_refs(strata: list[RegionStratumRow], passages: list[DeepPassageRow], below: list[EntityRow]) -> list[int]:
    found = {row.realm_entity_id for row in strata} | {entity.id for entity in below}
    for passage in passages:
        found |= {passage.first_region_entity_id, passage.second_region_entity_id, passage.place_entity_id, passage.dug_by_entity_id}
    return sorted(node for node in found if node is not None)


async def holder_below(session: AsyncSession, below: list[EntityRow], stratum: UndergroundStratum) -> int | None:
    for entity in below:
        if entity.stratum is stratum and entity.entity_type is EntityType.SETTLEMENT:
            folk = await people_of(session, entity)
            return await realm_of(session, entity.id) or (folk.id if folk is not None else None)
    return None


def passage_view(row: DeepPassageRow, region_id: int, named: dict[int, str]) -> DeepPassageView:
    near_first = row.first_region_entity_id == region_id and (
        row.second_region_entity_id != region_id or row.first_stratum is None or row.second_stratum is not None
    )
    near, far = (
        ((row.first_region_entity_id, row.first_stratum), (row.second_region_entity_id, row.second_stratum))
        if near_first
        else (
            (row.second_region_entity_id, row.second_stratum),
            (row.first_region_entity_id, row.first_stratum),
        )
    )
    return DeepPassageView(
        id=row.id,
        kind=passage_kind(near, far),
        state=row.state,
        origin=row.origin,
        width=row.width,
        progress=row.progress,
        near_stratum=near[1],
        far_region=ref(named, far[0]),
        far_stratum=far[1],
        place=ref(named, row.place_entity_id),
        digger=ref(named, row.dug_by_entity_id),
        locked=row.locked,
    )
