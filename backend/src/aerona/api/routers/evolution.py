from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.evolution import (
    CarrierView,
    CureResearchView,
    HerdRef,
    LineageMarkView,
    NodeEvolutionView,
    PathogenView,
    PlagueResponseView,
    ServiceView,
    SpeciesEcologyView,
    StockTraitView,
    SuccessionView,
    TraitPointView,
    TrophicView,
    WorldCycleView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.evolution import STAGE_COVER, trophic_level
from aerona.core.errors import NotFoundError
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import (
    CarrierRow,
    CureResearchRow,
    EcosystemServiceRow,
    LineageMarkRow,
    PlagueResponseRow,
    SpeciesTraitRow,
    TraitHistoryRow,
    TrophicLevelRow,
    WorldCycleRow,
)
from aerona.engine.disease.research import institutions
from aerona.rules.registry import Rules

router = APIRouter(tags=["evolution"])
NodeId = Annotated[int, Path(ge=1)]


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def trait_views(session: AsyncSession, rows: list[SpeciesTraitRow]) -> list[StockTraitView]:
    refs = await refs_for(session, [item for row in rows for item in (row.species_entity_id, row.region_entity_id)])
    return [
        StockTraitView(
            species=at(refs, row.species_entity_id),
            region=at(refs, row.region_entity_id),
            trait=row.trait,
            mean=row.mean,
            variance=row.variance,
            updated_epoch=row.updated_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def service_views(session: AsyncSession, rows: list[EcosystemServiceRow]) -> list[ServiceView]:
    refs = await refs_for(session, [item for row in rows for item in (row.region_entity_id, row.species_entity_id)])
    return [
        ServiceView(
            region=at(refs, row.region_entity_id),
            role=row.role,
            species=at(refs, row.species_entity_id),
            strength=row.strength,
            epoch=row.epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def herd_views(session: AsyncSession, rows: list[HerdRow]) -> list[HerdRef]:
    refs = await refs_for(session, [item for row in rows for item in (row.community_entity_id, row.species_entity_id)])
    return [HerdRef(community=at(refs, row.community_entity_id), species=at(refs, row.species_entity_id), head=row.head, stage=row.stage) for row in rows]


async def carrier_views(session: AsyncSession, rows: list[CarrierRow]) -> list[CarrierView]:
    refs = await refs_for(session, [item for row in rows for item in (row.mortal_entity_id, row.disease_entity_id, row.home_region_id)])
    return [
        CarrierView(
            mortal=at(refs, row.mortal_entity_id),
            disease=at(refs, row.disease_entity_id),
            home_region=at(refs, row.home_region_id),
            identified=row.identified,
            seeded=row.seeded,
            since_epoch=row.since_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def response_views(session: AsyncSession, rows: list[PlagueResponseRow]) -> list[PlagueResponseView]:
    refs = await refs_for(session, [item for row in rows for item in (row.community_entity_id, row.disease_entity_id)])
    return [
        PlagueResponseView(
            community=at(refs, row.community_entity_id),
            disease=at(refs, row.disease_entity_id),
            response=row.response,
            strength=row.strength,
            since_epoch=row.since_epoch,
            until_epoch=row.until_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def research_views(session: AsyncSession, rules: Rules, rows: list[CureResearchRow]) -> list[CureResearchView]:
    refs = await refs_for(session, [item for row in rows for item in (row.institution_entity_id, row.disease_entity_id)])
    return [
        CureResearchView(
            institution=at(refs, row.institution_entity_id),
            disease=at(refs, row.disease_entity_id),
            points=row.points,
            threshold=rules.cure_research.threshold,
            specimens=row.specimens,
            started_epoch=row.started_epoch,
            cured_epoch=row.cured_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def mark_views(session: AsyncSession, node_id: int) -> list[LineageMarkView]:
    rows = list(await session.scalars(select(LineageMarkRow).where(LineageMarkRow.species_entity_id == node_id).order_by(LineageMarkRow.package)))
    refs = await refs_for(session, [row.source_node_id for row in rows])
    return [
        LineageMarkView(package=row.package, blessing=row.blessing, source=at(refs, row.source_node_id), epoch=row.epoch, locked=list(row.locked))
        for row in rows
    ]


def ecology_view(profile: SpeciesProfileRow | None) -> SpeciesEcologyView | None:
    if profile is None:
        return None
    return SpeciesEcologyView(
        keystone=profile.keystone,
        feral_epoch=profile.feral_epoch,
        trophic_level=trophic_level(profile.diet, profile.size_class),
        stage=profile.stage,
        locked=[key for key in profile.locked if key in ("keystone", "feral_epoch")],
    )


def land_view(ground: RegionEnvironmentRow | None) -> SuccessionView | None:
    if ground is None:
        return None
    return SuccessionView(
        succession=ground.succession,
        succession_progress=ground.succession_progress,
        burned_epoch=ground.burned_epoch,
        stage_cover=STAGE_COVER[ground.succession],
        locked=[key for key in ground.locked if key in ("succession", "succession_progress")],
    )


def pathogen_view(profile: DiseaseProfileRow | None) -> PathogenView | None:
    if profile is None:
        return None
    return PathogenView(
        cold_tolerance=profile.cold_tolerance,
        heat_tolerance=profile.heat_tolerance,
        resistance=profile.resistance,
        locked=[key for key in profile.locked if key in ("cold_tolerance", "heat_tolerance", "resistance")],
    )


def cycle_view(row: WorldCycleRow | None) -> WorldCycleView | None:
    if row is None:
        return None
    return WorldCycleView(
        carbon=row.carbon,
        water=row.water,
        nutrients=row.nutrients,
        carbon_in=row.carbon_in,
        carbon_out=row.carbon_out,
        water_in=row.water_in,
        water_out=row.water_out,
        nutrients_in=row.nutrients_in,
        nutrients_out=row.nutrients_out,
        updated_epoch=row.updated_epoch,
        locked=list(row.locked),
    )


async def research_of(session: AsyncSession, node_id: int) -> list[CureResearchRow]:
    seats = [row.id for row in await institutions(session) if row.location_id == node_id]
    statement = select(CureResearchRow).where(or_(CureResearchRow.institution_entity_id.in_([node_id, *seats]), CureResearchRow.disease_entity_id == node_id))
    return list(await session.scalars(statement.order_by(CureResearchRow.institution_entity_id, CureResearchRow.disease_entity_id)))


@router.get("/evolution/of/{node_id}", response_model=NodeEvolutionView)
async def node_evolution(services: ServicesDep, node_id: NodeId) -> NodeEvolutionView:
    async with reader(services) as session:
        refs = await node_refs(session, [node_id])
        if node_id not in refs:
            raise NotFoundError("No such thing.")
        traits = select(SpeciesTraitRow).where(or_(SpeciesTraitRow.species_entity_id == node_id, SpeciesTraitRow.region_entity_id == node_id))
        services_rows = select(EcosystemServiceRow).where(
            or_(EcosystemServiceRow.region_entity_id == node_id, EcosystemServiceRow.species_entity_id == node_id)
        )
        herds = select(HerdRow).where(or_(HerdRow.community_entity_id == node_id, HerdRow.species_entity_id == node_id))
        carriers = select(CarrierRow).where(or_(CarrierRow.mortal_entity_id == node_id, CarrierRow.disease_entity_id == node_id))
        responses = select(PlagueResponseRow).where(or_(PlagueResponseRow.community_entity_id == node_id, PlagueResponseRow.disease_entity_id == node_id))
        entity = await session.get(EntityRow, node_id)
        return NodeEvolutionView(
            node=refs[node_id],
            history=[
                TraitPointView(trait=row.trait, epoch=row.epoch, value=row.value)
                for row in await session.scalars(
                    select(TraitHistoryRow).where(TraitHistoryRow.holder_entity_id == node_id).order_by(TraitHistoryRow.trait, TraitHistoryRow.epoch)
                )
            ],
            species=ecology_view(await session.get(SpeciesProfileRow, node_id)),
            traits=await trait_views(
                session,
                list(await session.scalars(traits.order_by(SpeciesTraitRow.species_entity_id, SpeciesTraitRow.region_entity_id, SpeciesTraitRow.trait))),
            ),
            marks=await mark_views(session, node_id),
            services=await service_views(
                session, list(await session.scalars(services_rows.order_by(EcosystemServiceRow.region_entity_id, EcosystemServiceRow.role)))
            ),
            trophic=[
                TrophicView(level=row.level, biomass=row.biomass, cap=row.cap, epoch=row.epoch)
                for row in await session.scalars(select(TrophicLevelRow).where(TrophicLevelRow.region_entity_id == node_id))
            ],
            land=land_view(await session.get(RegionEnvironmentRow, node_id)) if entity is not None else None,
            herds=await herd_views(session, list(await session.scalars(herds.order_by(HerdRow.community_entity_id, HerdRow.species_entity_id)))),
            pathogen=pathogen_view(await session.get(DiseaseProfileRow, node_id)),
            carriers=await carrier_views(session, list(await session.scalars(carriers.order_by(CarrierRow.mortal_entity_id, CarrierRow.disease_entity_id)))),
            responses=await response_views(
                session,
                list(
                    await session.scalars(
                        responses.order_by(PlagueResponseRow.community_entity_id, PlagueResponseRow.disease_entity_id, PlagueResponseRow.response)
                    )
                ),
            ),
            research=await research_views(session, services.rules.current, await research_of(session, node_id)),
            cycle=cycle_view(await session.get(WorldCycleRow, node_id)),
        )
