from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.regions import (
    HazardExposure,
    MapKnowledgeView,
    RealmChoice,
    RegionDangerView,
    RegionHazardView,
    RegionMemoryView,
    RegionTerrainView,
    RiverNeighbour,
)
from aerona.catalog.dangers import DANGERS, HAZARDS, MEMORY_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.region import PolityMapKnowledgeRow, RegionDangerRow, RegionHazardRow, RegionMemoryRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.region import DangerHarm
from aerona.engine.environment.dangers import harm_weight, total, weighted
from aerona.engine.environment.hazards import exposed
from aerona.engine.environment.knowledge import reveals
from aerona.engine.environment.memory import darkness, darkness_of, fades, holiness, holiness_of
from aerona.engine.environment.perils import haunt_factor
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
                harms={harm: round_half_up(row.strength * harm_weight(rules, row.source, harm) / PERCENT) for harm in DangerHarm},
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
                label=MEMORY_LABELS[row.kind],
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
            HazardExposure(hazard=hazard, label=spec.label, season=spec.season.value)
            for hazard, spec in HAZARDS.items()
            if exposed(rules, hazard, spec, ground)
        ],
        river_class=ground.river_class,
        river_neighbours=[
            RiverNeighbour(id=item, name=name, river_class=neighbours[item].river_class if item in neighbours else None)
            for item, name in neighbour_names.items()
        ],
    )
