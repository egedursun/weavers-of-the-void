from dataclasses import asdict, fields, is_dataclass
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Path, status
from sqlalchemy import select

from aerona.agents.celestial_deepener import SCALE_DEPTH_KINDS, deepen_celestial, scale_row
from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import JobAccepted
from aerona.api.schemas.cosmography import (
    CelestialReadingRecord,
    ClusterRecord,
    CosmicBeingRecord,
    CosmographyCatalog,
    CosmographyView,
    DimensionalEventRecord,
    DimensionRecord,
    FootprintRecord,
    GalacticEventRecord,
    GalaxyRecord,
    GalaxyShapeRecord,
    KindRecord,
    PhenomenonRecord,
    PlacementRecord,
    PullRecord,
    RiftRecord,
    ScaleWiki,
    StructureRecord,
)
from aerona.api.schemas.records import NodeRef, StarRecord
from aerona.api.views.common import chronicle_lines, images_of
from aerona.catalog.cosmography import (
    APOCALYPSE_LABELS,
    BARRED_GALAXIES,
    BEING_KINDS,
    CLUSTER_KINDS,
    DIMENSION_KINDS,
    DIMENSIONAL_EVENT_LABELS,
    GALACTIC_EVENT_LABELS,
    GALACTIC_ZONES,
    GALAXY_TYPES,
    PHENOMENON_KINDS,
    SPIRAL_GALAXIES,
    STRUCTURE_KINDS,
    KindSpec,
)
from aerona.catalog.travel import METHOD_REACH
from aerona.constants.api import WIKI_TIMELINE_LINES
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmography import (
    CelestialReadingRow,
    CosmicBeingProfileRow,
    DimensionalEventRow,
    GalacticEventRow,
    PhenomenonFootprintRow,
    PhenomenonProfileRow,
    RiftRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.job import JobKind
from aerona.engine.cosmos.kinds import (
    BEING_MECHANICS,
    CLUSTER_KIND_MECHANICS,
    DIMENSION_KIND_MECHANICS,
    GALAXY_TYPE_MECHANICS,
    PHENOMENON_MECHANICS,
    STRUCTURE_MECHANICS,
    ZONE_MECHANICS,
)
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.phases.doom import dominant_variant, doom_items
from aerona.engine.primitives.manual import manual_context
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.images.records import cover_of

router = APIRouter(tags=["cosmography"])
RECENT_EPOCHS = 10


def kinds[K: StrEnum](rules: Rules, specs: dict[K, KindSpec], mechanics: dict[K, Any] | None = None) -> list[KindRecord]:
    found: list[KindRecord] = []
    for kind, spec in specs.items():
        effects: dict[str, int] = {}
        row = mechanics.get(kind) if mechanics is not None else None
        if row is not None and is_dataclass(row):
            for item in fields(row):
                value = getattr(row, item.name)
                if callable(value):
                    effects[item.name] = int(value(rules))
        found.append(KindRecord(value=kind.value, label=spec.label, description=spec.description, effects=effects))
    return found


@router.get("/cosmography/catalog", response_model=CosmographyCatalog)
async def cosmography_catalog(services: ServicesDep) -> CosmographyCatalog:
    async with reader(services) as session:
        rules = await world_rules(services, session)
    return CosmographyCatalog(
        galaxy_types=kinds(rules, dict(GALAXY_TYPES), dict(GALAXY_TYPE_MECHANICS)),
        cluster_kinds=kinds(rules, dict(CLUSTER_KINDS), dict(CLUSTER_KIND_MECHANICS)),
        dimension_kinds=kinds(rules, dict(DIMENSION_KINDS), dict(DIMENSION_KIND_MECHANICS)),
        structure_kinds=kinds(rules, dict(STRUCTURE_KINDS), dict(STRUCTURE_MECHANICS)),
        zones=kinds(rules, dict(GALACTIC_ZONES), dict(ZONE_MECHANICS)),
        phenomenon_kinds=kinds(rules, dict(PHENOMENON_KINDS), dict(PHENOMENON_MECHANICS)),
        being_kinds=kinds(rules, dict(BEING_KINDS), dict(BEING_MECHANICS)),
        galactic_events=kinds(rules, dict(GALACTIC_EVENT_LABELS)),
        dimensional_events=kinds(rules, dict(DIMENSIONAL_EVENT_LABELS)),
        apocalypse_variants=kinds(rules, dict(APOCALYPSE_LABELS)),
        method_reach={method.value: reach for method, reach in METHOD_REACH.items()},
        shape=GalaxyShapeRecord(
            core_reach_pct=rules.galaxies.core_reach_pct,
            bulge_reach_pct=rules.galaxies.bulge_reach_pct,
            bar_reach_pct=rules.galaxies.bar_reach_pct,
            inner_reach_pct=rules.galaxies.inner_reach_pct,
            disc_reach_pct=rules.galaxies.disc_reach_pct,
            halo_reach_pct=rules.galaxies.halo_reach_pct,
            arm_width_deg=rules.galaxies.arm_width_deg,
            arm_wind_deg=rules.galaxies.arm_wind_deg,
            barred_types=sorted(BARRED_GALAXIES),
            spiral_types=sorted(SPIRAL_GALAXIES),
        ),
    )


@router.post("/cosmography/nodes/{node_id}/deepen", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def deepen_scale(services: ServicesDep, node_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Deepening a part of the heavens")
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None or node.kind not in SCALE_DEPTH_KINDS:
            raise NotFoundError("No such part of the heavens.")
        name, kind = node.name, SCALE_DEPTH_KINDS[node.kind]

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "deepen")
        await deepen_celestial(services.agents, kind, node_id)
        return {"node_id": node_id}

    return await submit(services, JobKind.DEEPEN, f"{kind.value}:{node_id}:depth", work, {"node_id": node_id}, label=f"deepening of {name}")


@router.get("/cosmography/nodes/{node_id}/wiki", response_model=ScaleWiki)
async def scale_wiki(services: ServicesDep, node_id: int = Path(ge=1)) -> ScaleWiki:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None or node.kind not in SCALE_DEPTH_KINDS:
            raise NotFoundError("No such part of the heavens.")
        name = node.name
        scale = await scale_row(session, SCALE_DEPTH_KINDS[node.kind], node_id)
        lines = (
            list(
                await session.scalars(
                    select(ChronicleRow)
                    .where(ChronicleRow.visible.is_(True), ChronicleRow.text.contains(name))
                    .order_by(ChronicleRow.id.desc())
                    .limit(WIKI_TIMELINE_LINES)
                )
            )
            if name
            else []
        )
        return ScaleWiki(
            node_id=node_id,
            kind=node.kind,
            depth=scale.depth if scale is not None else None,
            cover=await cover_of(session, node_id),
            images=await images_of(session, node_id),
            timeline=await chronicle_lines(session, lines),
        )


@router.get("/cosmography", response_model=CosmographyView)
async def cosmography(services: ServicesDep) -> CosmographyView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        cosmos = await CosmosRepository(session).require_cosmos()
        epoch = cosmos.epoch
        ladder = await Cosmography.load(session)
        recent = epoch - RECENT_EPOCHS
        galactic = list(await session.scalars(select(GalacticEventRow).where(GalacticEventRow.epoch >= recent).order_by(GalacticEventRow.id.desc())))
        planar = list(await session.scalars(select(DimensionalEventRow).where(DimensionalEventRow.epoch >= recent).order_by(DimensionalEventRow.id.desc())))
        rifts = list(await session.scalars(select(RiftRow).order_by(RiftRow.id)))
        names = {row.id: (row.name, row.world_id) for row in await session.scalars(select(EntityRow).where(EntityRow.status == EntityStatus.CANON))}
        beings = [
            CosmicBeingRecord.model_validate(row).model_copy(update={"name": names[row.entity_id][0], "world_id": names[row.entity_id][1]})
            for row in await session.scalars(select(CosmicBeingProfileRow).order_by(CosmicBeingProfileRow.entity_id))
            if row.entity_id in names
        ]
        prints: dict[int, list[FootprintRecord]] = {}
        for row in await session.scalars(select(PhenomenonFootprintRow).order_by(PhenomenonFootprintRow.region_entity_id)):
            prints.setdefault(row.phenomenon_entity_id, []).append(FootprintRecord.model_validate(row))
        phenomena = [
            PhenomenonRecord.model_validate(row).model_copy(
                update={"name": names[row.entity_id][0], "world_id": names[row.entity_id][1], "footprints": prints.get(row.entity_id, [])}
            )
            for row in await session.scalars(select(PhenomenonProfileRow).order_by(PhenomenonProfileRow.entity_id))
            if row.entity_id in names
        ]
        readings = [CelestialReadingRecord.model_validate(row) for row in await session.scalars(select(CelestialReadingRow))]
        people_names = {str(row.people_entity_id): names[row.people_entity_id][0] for row in readings if row.people_entity_id in names}
        ruler_ids = {row.ruler_node_id for row in ladder.dimensions.values() if row.ruler_node_id is not None}
        rulers = (
            {
                str(node.id): NodeRef(id=node.id, kind=node.kind, name=node.name)
                for node in await session.scalars(select(NodeRow).where(NodeRow.id.in_(ruler_ids)))
            }
            if ruler_ids
            else {}
        )
        placements = []
        for world in sorted(ladder.worlds.values(), key=lambda row: row.id):
            place = ladder.place_world(world)
            pull = ladder.pull(rules, place)
            placements.append(
                PlacementRecord(
                    world_id=world.id,
                    dimension_id=place.dimension_id,
                    cluster_id=place.cluster.id if place.cluster is not None else None,
                    top_cluster_id=place.top_cluster.id if place.top_cluster is not None else None,
                    galaxy_id=place.galaxy_id,
                    structure_id=place.structure.id if place.structure is not None else None,
                    star_id=place.star.id if place.star is not None else None,
                    zone=place.zone,
                    pull=PullRecord(**{key: value for key, value in asdict(pull).items() if key != "minerals"}),
                )
            )
        likely = dominant_variant(rules, await doom_items(await manual_context(session, "cosmography_view", rules), epoch + 1))
        return CosmographyView(
            epoch=epoch,
            dimensions=[DimensionRecord.model_validate(row) for row in ladder.dimensions.values()],
            clusters=[ClusterRecord.model_validate(row) for row in ladder.clusters.values()],
            galaxies=[GalaxyRecord.model_validate(row) for row in ladder.galaxies.values()],
            structures=[StructureRecord.model_validate(row) for row in ladder.structures.values()],
            galactic_events=[
                GalacticEventRecord.model_validate(row).model_copy(update={"active": row.until_epoch is None or row.until_epoch >= epoch}) for row in galactic
            ],
            dimensional_events=[
                DimensionalEventRecord.model_validate(row).model_copy(update={"active": row.until_epoch is None or row.until_epoch >= epoch}) for row in planar
            ],
            rifts=[RiftRecord.model_validate(row) for row in rifts],
            beings=beings,
            phenomena=phenomena,
            readings=readings,
            placements=placements,
            world_names={str(world.id): world.name for world in ladder.worlds.values()},
            star_names={str(star.id): star.name for star in ladder.stars.values()},
            people_names=people_names,
            rulers=rulers,
            stars=[StarRecord.model_validate(star) for star in ladder.stars.values()],
            apocalypse_variant=cosmos.apocalypse_variant,
            likely_variant=likely,
        )
