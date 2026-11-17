from collections.abc import Sequence
from dataclasses import asdict, fields, is_dataclass
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    HeldLawRecord,
    HostedStratumRecord,
    KindRecord,
    PhenomenonRecord,
    PlacementRecord,
    PullRecord,
    RiftRecord,
    ScaleWiki,
    SkyWorshipperRecord,
    SkyWorshipView,
    StructureRecord,
)
from aerona.api.schemas.records import NodeRef, StarRecord
from aerona.api.views.common import chronicle_lines, images_of, node_refs
from aerona.catalog.cosmography import (
    APOCALYPSE_LABELS,
    BARRED_GALAXIES,
    BEING_KINDS,
    BEING_MODEL,
    CLUSTER_KINDS,
    DIMENSION_KINDS,
    DIMENSIONAL_EVENT_LABELS,
    GALACTIC_EVENT_LABELS,
    GALACTIC_ZONES,
    GALAXY_TYPES,
    PHENOMENON_KINDS,
    PHENOMENON_MODEL,
    SPIRAL_GALAXIES,
    STRUCTURE_KINDS,
    KindSpec,
)
from aerona.catalog.knowledge import NATURAL_LAWS
from aerona.catalog.travel import METHOD_REACH
from aerona.constants.api import WIKI_TIMELINE_LINES
from aerona.core.errors import NotFoundError
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
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
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cosmography import SkyObject
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.node import NodeKind
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
from aerona.engine.phases.world_age import age_of, read_world_age
from aerona.engine.primitives.knowledge import laws_of_dimension
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import stat
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


async def actor_names(session: AsyncSession, galactic: Sequence[Any], planar: Sequence[Any], rifts: Sequence[Any]) -> dict[str, str]:
    ids = [
        node
        for node in (
            *(row.caused_by_node_id for row in galactic),
            *(node for row in planar for node in (row.caused_by_node_id, row.subject_entity_id)),
            *(row.opened_by_node_id for row in rifts),
        )
        if node is not None
    ]
    return {str(node): ref.name for node, ref in (await node_refs(session, ids)).items()}


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
                    select(ChronicleRow).where(shown_lines(), ChronicleRow.text.contains(name)).order_by(ChronicleRow.id.desc()).limit(WIKI_TIMELINE_LINES)
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
            laws=await held_laws(session, node_id) if node.kind is NodeKind.DIMENSION else [],
            strata=await hosted_strata(session, node_id) if node.kind is NodeKind.DIMENSION else [],
        )


async def hosted_strata(session: AsyncSession, dimension_id: int) -> list[HostedStratumRecord]:
    rows = list(await session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.dimension_id == dimension_id).order_by(AfterlifeStratumRow.id)))
    refs = await node_refs(session, [row.realm_entity_id for row in rows])
    return [HostedStratumRecord(id=row.id, name=row.name, kind=row.kind, population=row.population, realm=refs.get(row.realm_entity_id)) for row in rows]


SKY_KINDS: dict[NodeKind, SkyObject] = {NodeKind.STAR: SkyObject.STAR, NodeKind.GALAXY: SkyObject.GALAXY, NodeKind.DIMENSION: SkyObject.DIMENSION}
SKY_FLAGS: dict[SkyObject, EntityFlag] = {SkyObject.STAR: EntityFlag.WORSHIPS_STAR, SkyObject.GALAXY: EntityFlag.WORSHIPS_GALAXY}


def worshipper(row: EntityRow) -> SkyWorshipperRecord:
    return SkyWorshipperRecord(id=row.id, name=row.name, entity_type=row.entity_type, world_id=row.world_id, piety=stat(row, "piety"))


@router.get("/cosmography/nodes/{node_id}/worship", response_model=SkyWorshipView)
async def sky_worship(services: ServicesDep, node_id: int = Path(ge=1)) -> SkyWorshipView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None or node.kind not in SKY_KINDS:
            raise NotFoundError("No star, galaxy or dimension by that id.")
        sky = SKY_KINDS[node.kind]
        ladder = await Cosmography.load(session)
        communities = sorted(await canon(session, COMMUNITY_TYPES), key=lambda row: row.id)

        def under(row: EntityRow) -> bool:
            place = ladder.place_world_id(row.world_id)
            return {SkyObject.STAR: place.star is not None and place.star.id == node_id, SkyObject.GALAXY: place.galaxy_id == node_id}.get(sky, True)

        if sky is SkyObject.DIMENSION:
            statement = select(BondRow.source_node_id).where(
                BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == node_id
            )
            devoted = set(await session.scalars(statement))
        else:
            devoted = await flags_by_entity(session, SKY_FLAGS[sky])
        worshippers = [worshipper(row) for row in communities if row.id in devoted and under(row)]
        candidates = [worshipper(row) for row in communities if row.id not in devoted and under(row)]
        return SkyWorshipView(node_id=node_id, sky=sky, name=node.name, worshippers=worshippers, candidates=candidates)


async def held_laws(session: AsyncSession, dimension_id: int) -> list[HeldLawRecord]:
    held = await laws_of_dimension(session, dimension_id)
    names = await NodeRepository(session).names_of([row.entity_id for row in held if row.entity_id is not None])
    return [
        HeldLawRecord(
            law=row.law,
            label=NATURAL_LAWS[row.law].label,
            description=NATURAL_LAWS[row.law].effect,
            entity_id=row.entity_id,
            name=names.get(row.entity_id) if row.entity_id is not None else None,
            strength=row.strength,
        )
        for row in held
    ]


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
            CosmicBeingRecord.model_validate(row).model_copy(
                update={
                    "name": names[row.entity_id][0],
                    "world_id": names[row.entity_id][1],
                    "substrate": BEING_MODEL[row.being_kind].substrate,
                    "sense": BEING_MODEL[row.being_kind].sense,
                }
            )
            for row in await session.scalars(select(CosmicBeingProfileRow).order_by(CosmicBeingProfileRow.entity_id))
            if row.entity_id in names
        ]
        prints: dict[int, list[FootprintRecord]] = {}
        for row in await session.scalars(select(PhenomenonFootprintRow).order_by(PhenomenonFootprintRow.region_entity_id)):
            prints.setdefault(row.phenomenon_entity_id, []).append(FootprintRecord.model_validate(row))
        phenomena = [
            PhenomenonRecord.model_validate(row).model_copy(
                update={
                    "name": names[row.entity_id][0],
                    "world_id": names[row.entity_id][1],
                    "footprints": prints.get(row.entity_id, []),
                    **vars(PHENOMENON_MODEL[row.kind]),
                }
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
        view = await manual_context(session, "cosmography_view", rules)
        likely = dominant_variant(rules, await doom_items(view, age_of(await read_world_age(view, epoch + 1))))
        return CosmographyView(
            epoch=epoch,
            dimensions=[DimensionRecord.model_validate(row) for row in ladder.dimensions.values()],
            clusters=[
                ClusterRecord.model_validate(row).model_copy(update={"central_galaxy_id": central.id if (central := ladder.central_galaxy(row.id)) else None})
                for row in ladder.clusters.values()
            ],
            galaxies=[GalaxyRecord.model_validate(row) for row in ladder.galaxies.values()],
            structures=[StructureRecord.model_validate(row) for row in ladder.structures.values()],
            galactic_events=[
                GalacticEventRecord.model_validate(row).model_copy(update={"active": row.until_epoch is None or row.until_epoch >= epoch}) for row in galactic
            ],
            dimensional_events=[
                DimensionalEventRecord.model_validate(row).model_copy(update={"active": row.until_epoch is None or row.until_epoch >= epoch}) for row in planar
            ],
            rifts=[RiftRecord.model_validate(row) for row in rifts],
            actor_names=await actor_names(session, galactic, planar, rifts),
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
