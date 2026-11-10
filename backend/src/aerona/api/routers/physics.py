from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.physics import (
    FeatureRecord,
    FitRecord,
    HeavensPhysicsView,
    ImpactRecord,
    LifeRecord,
    ObserverSurveyView,
    OrbitRecord,
    StageSpan,
    StarPhysicsView,
    SurveyRecord,
    SystemMember,
    SystemView,
    TerraformRecord,
    TransitRecord,
    WorldPhysicsRecord,
    WorldPhysicsView,
)
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.flora import WorldBiochemistryRow
from aerona.db.tables.physics import (
    CosmicFeatureRow,
    ImpactEventRow,
    StarPhysicsRow,
    StarSystemRow,
    TerraformingRow,
    WorldLifeRow,
    WorldPhysicsRow,
    WorldSurveyRow,
)
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import ClimateEra
from aerona.engine.cosmos.eras import emergent_era
from aerona.engine.cosmos.lifeforms import world_fit
from aerona.engine.cosmos.orbits import eclipse_period, next_epoch, transit_pairs, transit_phase
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.stellar import ends_in_supernova, engulf_orbit, giant_for, remnant_for, stage_length, typical_mass
from aerona.engine.cosmos.systems import members

router = APIRouter(tags=["physics"])
STAGES = (StarAge.YOUNG, StarAge.MAIN, StarAge.OLD, StarAge.DYING)


def feature_ids(row: CosmicFeatureRow) -> list[int]:
    return [item for item in (row.star_id, row.world_id, row.world_b_id, row.entity_id) if item is not None]


async def feature_records(session: AsyncSession, rows: list[CosmicFeatureRow]) -> list[FeatureRecord]:
    refs = await node_refs(session, [item for row in rows for item in feature_ids(row)])
    return [
        FeatureRecord(
            id=row.id,
            kind=row.kind,
            name=row.name,
            galaxy_id=row.galaxy_id,
            star=refs.get(row.star_id) if row.star_id is not None else None,
            world=refs.get(row.world_id) if row.world_id is not None else None,
            world_b=refs.get(row.world_b_id) if row.world_b_id is not None else None,
            body=refs.get(row.entity_id) if row.entity_id is not None else None,
            route_id=row.route_id,
            x=row.x,
            y=row.y,
            description=row.description,
            radius=row.radius,
            density=row.density,
            radiation=row.radiation,
            travel=row.travel,
            omen_weight=row.omen_weight,
            richness=row.richness,
            pirates=row.pirates,
            instability=row.instability,
            period_epochs=row.period_epochs,
            next_return_epoch=row.next_return_epoch,
            created_epoch=row.created_epoch,
            ended_epoch=row.ended_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def impact_records(session: AsyncSession, rows: list[ImpactEventRow]) -> list[ImpactRecord]:
    ids = [item for row in rows for item in (row.world_id, row.region_entity_id, row.crater_place_id, row.deflected_by_node_id, row.called_by_node_id) if item]
    refs = await node_refs(session, ids)
    return [
        ImpactRecord(
            id=row.id,
            world=refs.get(row.world_id),
            region=refs.get(row.region_entity_id) if row.region_entity_id is not None else None,
            feature_id=row.feature_id,
            body=row.body,
            size=row.size,
            due_epoch=row.due_epoch,
            warned_epoch=row.warned_epoch,
            outcome=row.outcome,
            crater=refs.get(row.crater_place_id) if row.crater_place_id is not None else None,
            winter_epochs=row.winter_epochs,
            deflected_by=refs.get(row.deflected_by_node_id) if row.deflected_by_node_id is not None else None,
            called_by=refs.get(row.called_by_node_id) if row.called_by_node_id is not None else None,
            text=row.text,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def terraform_records(session: AsyncSession, rows: list[TerraformingRow]) -> list[TerraformRecord]:
    refs = await node_refs(session, [item for row in rows for item in (row.world_id, row.by_node_id) if item is not None])
    return [
        TerraformRecord(
            id=row.id,
            world=refs.get(row.world_id),
            aim=row.aim,
            by=refs.get(row.by_node_id) if row.by_node_id is not None else None,
            step=row.step,
            epochs_left=row.epochs_left,
            started_epoch=row.started_epoch,
            locked=list(row.locked),
        )
        for row in rows
    ]


async def survey_records(session: AsyncSession, rows: list[WorldSurveyRow]) -> list[SurveyRecord]:
    refs = await node_refs(session, [item for row in rows for item in (row.observer_entity_id, row.world_id)])
    return [
        SurveyRecord(
            id=row.id, observer=refs.get(row.observer_entity_id), world=refs.get(row.world_id), level=row.level, epoch=row.epoch, locked=list(row.locked)
        )
        for row in rows
    ]


async def system_view(session: AsyncSession, system: StarSystemRow, stars: dict[int, StarRow], physics: dict[int, StarPhysicsRow]) -> SystemView:
    return SystemView(
        id=system.id,
        name=system.name,
        galaxy_id=system.galaxy_id,
        x=system.x,
        y=system.y,
        separation=system.separation,
        band_inner=system.band_inner,
        band_outer=system.band_outer,
        created_epoch=system.created_epoch,
        locked=list(system.locked),
        members=[
            SystemMember(
                star_id=star_id,
                name=stars[star_id].name,
                star_type=stars[star_id].star_type,
                role=physics[star_id].role,
                mass=physics[star_id].mass,
                luminosity=physics[star_id].luminosity,
            )
            for star_id in members(physics, system.id)
            if star_id in stars
        ],
    )


async def star_tables(session: AsyncSession) -> tuple[dict[int, StarRow], dict[int, StarPhysicsRow]]:
    stars = {row.id: row for row in await session.scalars(select(StarRow).order_by(StarRow.id))}
    physics = {row.star_id: row for row in await session.scalars(select(StarPhysicsRow))}
    return stars, physics


@router.get("/physics/stars/{star_id}", response_model=StarPhysicsView)
async def star_physics(services: ServicesDep, star_id: int = Path(ge=1)) -> StarPhysicsView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        star = await session.get(StarRow, star_id)
        if star is None:
            raise NotFoundError("No such star.")
        stars, physics = await star_tables(session)
        row = physics.get(star.id)
        mass = row.mass if row is not None else typical_mass(rules, star.star_type)
        stages = [StageSpan(stage=stage, epochs=stage_length(rules, mass, stage) or 0) for stage in STAGES]
        system = await session.get(StarSystemRow, row.system_id) if row is not None and row.system_id is not None else None
        cosmography = await Cosmography.load(session)
        worlds = [world for world in cosmography.worlds.values() if (place := cosmography.place_world(world)).star is not None and place.star.id == star.id]
        world_rows = {
            item.world_id: item for item in await session.scalars(select(WorldPhysicsRow).where(WorldPhysicsRow.world_id.in_([world.id for world in worlds])))
        }
        features = list(await session.scalars(select(CosmicFeatureRow).where(CosmicFeatureRow.star_id == star.id).order_by(CosmicFeatureRow.id)))
        maker = (await node_refs(session, [row.maker_son_id])).get(row.maker_son_id) if row is not None and row.maker_son_id is not None else None
        return StarPhysicsView(
            star_id=star.id,
            name=star.name,
            star_type=star.star_type,
            age_stage=star.age_stage,
            mass=mass,
            metallicity=row.metallicity if row is not None else 0,
            age_epochs=row.age_epochs if row is not None else 0,
            luminosity=row.luminosity if row is not None else 0.0,
            lifetime_epochs=row.lifetime_epochs if row is not None else 0,
            band_inner=row.band_inner if row is not None else 0.0,
            band_outer=row.band_outer if row is not None else 0.0,
            maker=maker,
            upkeep=row.upkeep if row is not None else 0,
            locked=list(row.locked) if row is not None else [],
            stages=stages,
            giant=giant_for(rules, mass),
            remnant=remnant_for(rules, mass),
            supernova=ends_in_supernova(rules, mass),
            engulf_orbit=engulf_orbit(rules, mass),
            system=await system_view(session, system, stars, physics) if system is not None else None,
            orbits=[
                OrbitRecord(
                    world_id=world.id,
                    name=world.name,
                    orbit=world.orbit,
                    eccentricity=world_rows[world.id].eccentricity if world.id in world_rows else 0.0,
                    inclination=world_rows[world.id].inclination if world.id in world_rows else 0.0,
                    parent_world_id=world.parent_world_id,
                    habitable=world_rows[world.id].habitable if world.id in world_rows else False,
                    ringed=world_rows[world.id].ringed if world.id in world_rows else False,
                    tidally_locked=world_rows[world.id].tidally_locked if world.id in world_rows else False,
                    circumbinary=world_rows[world.id].circumbinary if world.id in world_rows else False,
                )
                for world in sorted(worlds, key=lambda item: (item.parent_world_id is not None, item.orbit, item.id))
            ],
            features=await feature_records(session, features),
        )


def physics_record(row: WorldPhysicsRow) -> WorldPhysicsRecord:
    return WorldPhysicsRecord.model_validate(row, from_attributes=True)


@router.get("/physics/worlds/{world_id}", response_model=WorldPhysicsView)
async def world_physics(services: ServicesDep, world_id: int = Path(ge=1)) -> WorldPhysicsView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        world = await session.get(WorldRow, world_id)
        if world is None:
            raise NotFoundError("No such world.")
        physics = await session.get(WorldPhysicsRow, world.id)
        life = await session.get(WorldLifeRow, world.id)
        chemistries = sorted(await session.scalars(select(WorldBiochemistryRow.biochemistry).where(WorldBiochemistryRow.world_id == world.id)))
        projects = list(await session.scalars(select(TerraformingRow).where(TerraformingRow.world_id == world.id).order_by(TerraformingRow.id)))
        impacts = list(
            await session.scalars(
                select(ImpactEventRow).where(ImpactEventRow.world_id == world.id).order_by(ImpactEventRow.due_epoch.desc(), ImpactEventRow.id)
            )
        )
        surveys = list(await session.scalars(select(WorldSurveyRow).where(WorldSurveyRow.world_id == world.id).order_by(WorldSurveyRow.id)))
        peoples = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        refs = await node_refs(session, [people.id for people in peoples])
        fits = [
            FitRecord(people=refs[people.id], fit=world_fit(rules, await session.get(PeopleBiologyRow, people.id), physics, tuple(chemistries)))
            for people in peoples
            if people.id in refs
        ]
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
        period = eclipse_period(rules, physics, star)
        cosmography = await Cosmography.load(session)
        skies = {row.world_id: row for row in await session.scalars(select(WorldPhysicsRow))}
        pairs = [(inner, every) for outer, inner, every in transit_pairs(rules, list(cosmography.worlds.values()), skies) if outer.id == world.id]
        inner_refs = await node_refs(session, [inner.id for inner, _every in pairs])
        return WorldPhysicsView(
            epoch=epoch,
            world_id=world.id,
            name=world.name,
            year_length_days=world.year_length_days,
            day_length_hours=world.day_length_hours,
            season_count=world.season_count,
            axial_tilt=world.axial_tilt,
            tidal_strength=world.tidal_strength,
            calendar_locked=list(world.calendar_locked),
            icebound=physics is not None and emergent_era(rules, physics) is ClimateEra.ICE_AGE,
            next_eclipse_epoch=next_epoch(epoch, period, world.id) if period is not None else None,
            transits=[
                TransitRecord(inner=inner_refs[inner.id], next_epoch=next_epoch(epoch, every, transit_phase(world, inner)))
                for inner, every in pairs
                if inner.id in inner_refs
            ],
            physics=physics_record(physics) if physics is not None else None,
            life=LifeRecord(complexity=life.complexity, environments=list(life.environments), biochemistries=chemistries, locked=list(life.locked))
            if life is not None
            else None,
            terraforming=await terraform_records(session, projects),
            impacts=await impact_records(session, impacts),
            surveys=await survey_records(session, surveys),
            fits=fits,
        )


@router.get("/physics/heavens", response_model=HeavensPhysicsView)
async def heavens_physics(services: ServicesDep) -> HeavensPhysicsView:
    async with reader(services) as session:
        stars, physics = await star_tables(session)
        systems = list(await session.scalars(select(StarSystemRow).order_by(StarSystemRow.id)))
        features = list(await session.scalars(select(CosmicFeatureRow).order_by(CosmicFeatureRow.id)))
        impacts = list(await session.scalars(select(ImpactEventRow).order_by(ImpactEventRow.due_epoch.desc(), ImpactEventRow.id)))
        projects = list(await session.scalars(select(TerraformingRow).order_by(TerraformingRow.id)))
        return HeavensPhysicsView(
            epoch=(await CosmosRepository(session).require_cosmos()).epoch,
            systems=[await system_view(session, system, stars, physics) for system in systems],
            features=await feature_records(session, features),
            impacts=await impact_records(session, impacts),
            terraforming=await terraform_records(session, projects),
        )


@router.get("/physics/observers/{entity_id}/surveys", response_model=ObserverSurveyView)
async def observer_surveys(services: ServicesDep, entity_id: int = Path(ge=1)) -> ObserverSurveyView:
    async with reader(services) as session:
        observer = await session.get(EntityRow, entity_id)
        if observer is None:
            raise NotFoundError("No such record.")
        rows = list(await session.scalars(select(WorldSurveyRow).where(WorldSurveyRow.observer_entity_id == observer.id).order_by(WorldSurveyRow.world_id)))
        return ObserverSurveyView(observer_id=observer.id, surveys=await survey_records(session, rows))
