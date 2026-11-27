from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.cosmos import (
    AddictionView,
    CampaignMark,
    CosmosView,
    CosmosWorld,
    CravingImmunityView,
    DiscoverySummary,
    DiscoveryWorld,
    MigrationMark,
    OrbitMark,
    SensedWorld,
    SkyEventRecord,
    TravellerGuideView,
    WorldLaw,
    WorldPulseView,
    WorldTypeLook,
)
from aerona.api.schemas.records import EntitySummary, JourneyRecord, NodeRef, StarRecord, WorldRecord
from aerona.api.views.celestial import count_types, worlds_counts
from aerona.api.views.common import foreign_god_records, node_refs, route_records
from aerona.cartography.palette import palette_for
from aerona.catalog.worlds import WORLD_TYPES
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.cosmic_state import AddictionImmunityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow, OrbitalControlRow
from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow, RouteRow
from aerona.db.tables.society import AddictionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.economy import ADDICTION_HOLD
from aerona.engine.phases.doom import doom_forecast
from aerona.engine.phases.world_balance import son_shares, world_pulse
from aerona.engine.primitives.ledger import DoomItem
from aerona.services.codex import traveller_guide
from aerona.services.container import Services
from aerona.services.images.records import covers_of
from aerona.services.state_memo import per_state

router = APIRouter(tags=["cosmos"])

COSMOS_KEY = "cosmos"

WID = {"world_id": "world_id"}
PLACE_TYPES = (EntityType.REGION, EntityType.PLACE)
COMMUNITY_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION)

ALIASES = (
    Alias("POST", "/worlds", "create_world"),
    Alias("PATCH", "/worlds/{world_id}", "world:edit", path_fields=WID),
    Alias("PUT", "/worlds/{world_id}/orbit", "world:orbit", path_fields=WID),
    Alias("POST", "/worlds/{world_id}/wrath", "wrath:world", path_fields=WID),
    Alias("POST", "/worlds/{world_id}/discovery-round", "discovery_round", path_fields=WID),
    Alias("PATCH", "/stars/{star_id}", "star:edit", path_fields={"star_id": "star_id"}),
    Alias("DELETE", "/stars/{star_id}", "star:delete", path_fields={"star_id": "star_id"}),
    Alias("POST", "/routes", "route:open"),
    Alias("POST", "/routes/{route_id}/sever", "route", path_fields={"route_id": "route_id"}, fixed={"action": "sever"}, summary="Sever a route"),
    Alias("POST", "/routes/{route_id}/restore", "route", path_fields={"route_id": "route_id"}, fixed={"action": "reopen"}, summary="Reopen a route"),
    Alias("POST", "/routes/{route_id}/reveal", "route", path_fields={"route_id": "route_id"}, fixed={"action": "reveal"}, summary="Reveal a hidden route"),
    Alias("POST", "/voyages/{journey_id}/recall", "journey:recall", path_fields={"journey_id": "journey_id"}),
    Alias("PUT", "/climate", "climate"),
    Alias("PUT", "/cosmic-resource", "cosmos:resource"),
    Alias("POST", "/cosmic-resource/deposits", "cosmos:deposit"),
    Alias("POST", "/cosmic/hang-star", "cosmic:hang_star"),
    Alias("POST", "/cosmic/seal-gate", "cosmic:seal_gate"),
    Alias("POST", "/cosmic/cleanse-leak", "cosmic:cleanse_leak"),
    Alias("POST", "/cosmic/forget-world", "cosmic:forget_world"),
    Alias("POST", "/cosmic/sky-event", "cosmic:sky_event"),
    Alias("POST", "/cosmic/rekindle-star", "cosmic:rekindle_star"),
    Alias("POST", "/cosmic/soul-bind", "cosmic:soul_bind"),
    Alias("POST", "/cosmic/legendary-quest", "cosmic:legendary_quest"),
)


async def campaign_marks(session: AsyncSession, rows: list[InterworldCampaignRow]) -> list[CampaignMark]:
    attackers = sorted({row.attacker_entity_id for row in rows})
    names = {entity.id: entity.name for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(attackers)).order_by(EntityRow.id))}
    return [
        CampaignMark(
            id=row.id,
            attacker_entity_id=row.attacker_entity_id,
            attacker_name=names.get(row.attacker_entity_id, ""),
            from_world_id=row.from_world_id,
            target_world_id=row.target_world_id,
            stage=row.stage,
            forces=row.forces,
        )
        for row in rows
    ]


@router.get("/worlds/{world_id}/laws", response_model=list[WorldLaw])
async def world_laws(services: ServicesDep, world_id: int = Path(ge=1)) -> list[WorldLaw]:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        rows = await session.scalars(
            select(EntityRow)
            .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_((EntityType.NATURAL_LAW, EntityType.LAW)))
            .order_by(EntityRow.id)
        )
        return [WorldLaw(entity=EntitySummary.model_validate(row), mechanic=row.natural_law) for row in rows]


@router.get("/addictions", response_model=list[AddictionView])
async def addictions(services: ServicesDep, community_id: Annotated[int | None, Query(ge=1)] = None) -> list[AddictionView]:
    async with reader(services) as session:
        statement = select(AddictionRow).where(AddictionRow.addicted_since_epoch.is_not(None))
        if community_id is not None:
            statement = statement.where(AddictionRow.community_entity_id == community_id)
        rows = list(await session.scalars(statement.order_by(AddictionRow.addicted_since_epoch, AddictionRow.community_entity_id)))
        refs = await node_refs(session, [node for row in rows for node in (row.community_entity_id, row.resource_entity_id)])
        return [
            AddictionView(
                community=refs[row.community_entity_id],
                resource=refs[row.resource_entity_id],
                owned_epochs=row.owned_epochs,
                addicted_since_epoch=row.addicted_since_epoch,
                withdrawal_since_epoch=row.withdrawal_since_epoch,
                held=ADDICTION_HOLD in row.locked,
            )
            for row in rows
            if row.community_entity_id in refs and row.resource_entity_id in refs
        ]


@router.get("/addiction-immunities", response_model=list[CravingImmunityView])
async def addiction_immunities(services: ServicesDep, community_id: Annotated[int | None, Query(ge=1)] = None) -> list[CravingImmunityView]:
    async with reader(services) as session:
        statement = select(AddictionImmunityRow)
        if community_id is not None:
            statement = statement.where(AddictionImmunityRow.community_entity_id == community_id)
        rows = list(await session.scalars(statement.order_by(AddictionImmunityRow.recovered_epoch.desc(), AddictionImmunityRow.community_entity_id)))
        refs = await node_refs(session, [node for row in rows for node in (row.community_entity_id, row.resource_entity_id)])
        return [
            CravingImmunityView(community=refs[row.community_entity_id], resource=refs[row.resource_entity_id], recovered_epoch=row.recovered_epoch)
            for row in rows
            if row.community_entity_id in refs and row.resource_entity_id in refs
        ]


class DoomPart(ApiModel):
    key: str
    label: DoomItem
    value: float


class DoomForecastView(ApiModel):
    clock: int
    threshold: int
    speed_pct: int
    raw: float
    step: float
    epochs_left: float | None
    parts: list[DoomPart]


@router.get("/doom", response_model=DoomForecastView)
async def read_doom(services: ServicesDep) -> DoomForecastView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        forecast = await doom_forecast(session, rules)
    remaining = forecast.threshold - forecast.clock
    return DoomForecastView(
        clock=forecast.clock,
        threshold=forecast.threshold,
        speed_pct=forecast.speed_pct,
        raw=forecast.raw,
        step=forecast.step,
        epochs_left=remaining / forecast.step if forecast.step > 0 else None,
        parts=[DoomPart(key=item.name.lower(), label=item, value=value) for item, value in forecast.items],
    )


@router.get("/cosmos", response_model=CosmosView)
async def read_cosmos(services: ServicesDep) -> CosmosView:
    return await per_state(services.database, COSMOS_KEY, lambda: cosmos_view(services))


async def cosmos_view(services: Services) -> CosmosView:
    async with reader(services) as session:
        worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
        sons = list(await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))
        counts = await worlds_counts(session, [world.id for world in worlds])
        world_covers = await covers_of(session, [world.id for world in worlds])
        cosmos_worlds = [
            CosmosWorld(
                world=WorldRecord.model_validate(world),
                type_label=WORLD_TYPES[world.world_type].label,
                counts=counts[world.id],
                sons=[NodeRef(id=son.id, kind=son.kind, name=son.name) for son in sons if son.current_world_id == world.id],
                cover=world_covers.get(world.id),
            )
            for world in worlds
        ]
        canon = select(EntityRow).where(EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        open_campaigns = select(InterworldCampaignRow).where(InterworldCampaignRow.ended_epoch.is_(None)).order_by(InterworldCampaignRow.id)
        open_migrations = select(InterworldMigrationRow).where(InterworldMigrationRow.ended_epoch.is_(None)).order_by(InterworldMigrationRow.id)
        star_rows = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
        star_covers = await covers_of(session, [row.id for row in star_rows])
        return CosmosView(
            stars=[StarRecord.model_validate(row).model_copy(update={"cover": star_covers.get(row.id)}) for row in star_rows],
            worlds=cosmos_worlds,
            foreign_gods=await foreign_god_records(session),
            routes=await route_records(session, await world_rules(services, session), list(await session.scalars(select(RouteRow).order_by(RouteRow.id)))),
            journeys=[JourneyRecord.model_validate(row) for row in await session.scalars(select(JourneyRow).order_by(JourneyRow.id.desc()))],
            sky_events=[SkyEventRecord.model_validate(row) for row in await session.scalars(select(SkyEventRow).order_by(SkyEventRow.id.desc()))],
            world_types=[WorldTypeLook(world_type=kind, label=spec.label, palette=palette_for(kind)) for kind, spec in WORLD_TYPES.items()],
            places=[EntitySummary.model_validate(row) for row in await session.scalars(canon.where(EntityRow.entity_type.in_(PLACE_TYPES)))],
            communities=[EntitySummary.model_validate(row) for row in await session.scalars(canon.where(EntityRow.entity_type.in_(COMMUNITY_TYPES)))],
            campaigns=await campaign_marks(session, list(await session.scalars(open_campaigns))),
            migrations=[MigrationMark.model_validate(row) for row in await session.scalars(open_migrations)],
            orbits=[OrbitMark.model_validate(row) for row in await session.scalars(select(OrbitalControlRow).order_by(OrbitalControlRow.id))],
        )


@router.get("/discovery-summary", response_model=DiscoverySummary)
async def discovery_summary(services: ServicesDep) -> DiscoverySummary:
    async with reader(services) as session:
        worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
        sensed = await session.scalars(select(HorizonIntuitionRow).order_by(HorizonIntuitionRow.id.desc()))
        return DiscoverySummary(
            worlds=[
                DiscoveryWorld(
                    world_id=world.id,
                    name=world.name,
                    discovery=world.discovery,
                    regions=await count_types(session, world.id, (EntityType.REGION,)),
                    places=await count_types(session, world.id, (EntityType.PLACE,)),
                    communities=await count_types(session, world.id, COMMUNITY_TYPES),
                )
                for world in worlds
            ],
            sensed=[SensedWorld.model_validate(row) for row in sensed],
        )


@router.get("/worlds/{world_id}/guide", response_model=TravellerGuideView)
async def world_guide(services: ServicesDep, world_id: int = Path(ge=1)) -> TravellerGuideView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        guide = await traveller_guide(session, rules, world_id)
    return TravellerGuideView(
        world=WorldRecord.model_validate(guide.world),
        type_label=guide.type_label,
        star=guide.star,
        star_type=guide.star_type,
        parent=guide.parent,
        atmosphere=guide.atmosphere,
        gravity=guide.gravity,
        discovery=guide.discovery,
        climate=guide.climate,
        climate_epochs_left=guide.climate_epochs_left,
        dangers=guide.dangers,
        peoples=guide.peoples,
        resources=guide.resources,
        routes=guide.routes,
        foreign_gods=guide.foreign_gods,
        sky=[EntitySummary.model_validate(row) for row in guide.sky],
    )


mount_all(router, ALIASES, tag="cosmos")


@router.get("/worlds/{world_id}/pulse", response_model=WorldPulseView)
async def world_pulse_view(services: ServicesDep, world_id: int = Path(ge=1)) -> WorldPulseView:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        rules = await world_rules(services, session)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        pulse = await world_pulse(session, rules, world_id, epoch)
        share = next((item.share for item in await son_shares(session, rules, epoch) if item.world_id == world_id), None)
    return WorldPulseView(
        world_id=pulse.world_id,
        communities=pulse.communities,
        godless=pulse.godless,
        factions=pulse.factions,
        cults=pulse.cults,
        named_mortals=pulse.named_mortals,
        sons=pulse.sons,
        son_share=share,
        engine_records=pulse.engine_records,
        this_epoch=pulse.this_epoch,
        per_epoch=pulse.per_epoch,
        quota=pulse.quota,
        window=pulse.window,
    )
