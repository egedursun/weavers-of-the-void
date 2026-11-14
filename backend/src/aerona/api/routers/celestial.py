from typing import Any

from fastapi import APIRouter, Path, status
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.celestial_deepener import deepen_celestial
from aerona.api.background import require_llm, submit
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.celestial import OrbitingWorld, PeopleBrief, StarWiki, WorldWiki
from aerona.api.schemas.common import JobAccepted
from aerona.api.schemas.cosmos import SkyEventRecord
from aerona.api.schemas.records import EntitySummary, StarRecord, WorldRecord
from aerona.api.views.celestial import population, world_counts
from aerona.api.views.common import chronicle_lines, foreign_god_record, images_of, node_ref, route_records
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.api import WIKI_PEOPLES_SHOWN, WIKI_TIMELINE_LINES
from aerona.core.errors import NotFoundError
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.primitives.stats import stat
from aerona.jobs.context import JobContext
from aerona.prompts.contexts.narrative import CelestialKind
from aerona.services.images.records import cover_of, covers_of

router = APIRouter(tags=["celestial"])

NO_WORLD = "No such world."
NO_STAR = "No such star."


async def require_world(session: AsyncSession, world_id: int) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError(NO_WORLD)
    return world


async def require_star(session: AsyncSession, star_id: int) -> StarRow:
    star = await session.get(StarRow, star_id)
    if star is None:
        raise NotFoundError(NO_STAR)
    return star


async def sky_events(session: AsyncSession, *, world_ids: list[int], star_id: int | None) -> list[SkyEventRecord]:
    conditions: list[ColumnElement[bool]] = [SkyEventRow.world_id.in_(world_ids)] if world_ids else []
    if star_id is not None:
        conditions.append(SkyEventRow.star_id == star_id)
    if not conditions:
        return []
    rows = await session.scalars(select(SkyEventRow).where(or_(*conditions)).order_by(SkyEventRow.epoch.desc(), SkyEventRow.id.desc()))
    return [SkyEventRecord.model_validate(row) for row in rows]


@router.get("/worlds/{world_id}/wiki", response_model=WorldWiki)
async def world_wiki(services: ServicesDep, world_id: int = Path(ge=1)) -> WorldWiki:
    async with reader(services) as session:
        world = await require_world(session, world_id)
        star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
        sons = await session.scalars(select(SonRow).where(SonRow.current_world_id == world.id, SonRow.status != SonStatus.DEAD).order_by(SonRow.id))
        gods = await session.scalars(select(ForeignGodRow).where(ForeignGodRow.world_id == world.id).order_by(ForeignGodRow.id))
        routes = await session.scalars(select(RouteRow).where(or_(RouteRow.world_a_id == world.id, RouteRow.world_b_id == world.id)).order_by(RouteRow.id))
        peoples = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
            )
        )
        peoples.sort(key=lambda people: stat(people, "population") or 0, reverse=True)
        shown = peoples[:WIKI_PEOPLES_SHOWN]
        covers = await covers_of(session, [people.id for people in shown])
        lines = list(
            await session.scalars(
                select(ChronicleRow).where(shown_lines(), ChronicleRow.world_id == world.id).order_by(ChronicleRow.id.desc()).limit(WIKI_TIMELINE_LINES)
            )
        )
        return WorldWiki(
            world=WorldRecord.model_validate(world),
            type_label=WORLD_TYPES[world.world_type].label,
            cover=await cover_of(session, world.id),
            depth=world.depth,
            star=StarRecord.model_validate(star) if star is not None else None,
            counts=await world_counts(session, world.id),
            sons=[ref for son in sons if (ref := await node_ref(session, son.id)) is not None],
            patron=await node_ref(session, world.patron_son_id),
            foreign_gods=[await foreign_god_record(session, god) for god in gods],
            routes=await route_records(session, await world_rules(services, session), list(routes)),
            peoples=[
                PeopleBrief(entity=EntitySummary.model_validate(people), population=round(stat(people, "population") or 0), cover=covers.get(people.id))
                for people in shown
            ],
            sky_events=await sky_events(session, world_ids=[world.id], star_id=None),
            timeline=await chronicle_lines(session, lines),
            images=await images_of(session, world.id),
        )


@router.get("/stars/{star_id}/wiki", response_model=StarWiki)
async def star_wiki(services: ServicesDep, star_id: int = Path(ge=1)) -> StarWiki:
    async with reader(services) as session:
        star = await require_star(session, star_id)
        worlds = list(
            await session.scalars(
                select(WorldRow).where(WorldRow.star_id == star.id).order_by(WorldRow.parent_world_id.is_not(None), WorldRow.orbit, WorldRow.id)
            )
        )
        covers = await covers_of(session, [world.id for world in worlds])
        lines = list(
            await session.scalars(
                select(ChronicleRow)
                .where(shown_lines(), ChronicleRow.kind == ChronicleKind.STAR, ChronicleRow.text.contains(star.name))
                .order_by(ChronicleRow.id.desc())
                .limit(WIKI_TIMELINE_LINES)
            )
        )
        return StarWiki(
            star=StarRecord.model_validate(star),
            type_label=STAR_TYPE_LABELS[star.star_type],
            cover=await cover_of(session, star.id),
            depth=star.depth,
            worlds=[
                OrbitingWorld(
                    world=WorldRecord.model_validate(world),
                    type_label=WORLD_TYPES[world.world_type].label,
                    cover=covers.get(world.id),
                    population=await population(session, world.id),
                )
                for world in worlds
            ],
            sky_events=await sky_events(session, world_ids=[world.id for world in worlds], star_id=star.id),
            timeline=await chronicle_lines(session, lines),
            images=await images_of(session, star.id),
        )


@router.post("/worlds/{world_id}/deepen", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def deepen_world(services: ServicesDep, world_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Deepening a world")
    async with reader(services) as session:
        world = await require_world(session, world_id)
        name = world.name

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "deepen")
        await deepen_celestial(services.agents, CelestialKind.WORLD, world_id)
        return {"world_id": world_id}

    return await submit(services, JobKind.DEEPEN, f"world:{world_id}:depth", work, {"world_id": world_id}, label=f"deepening of {name}")


@router.post("/stars/{star_id}/deepen", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def deepen_star(services: ServicesDep, star_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "Deepening a star")
    async with reader(services) as session:
        star = await require_star(session, star_id)
        name = star.name

    async def work(context: JobContext) -> dict[str, Any]:
        context.report(0.0, "deepen")
        await deepen_celestial(services.agents, CelestialKind.STAR, star_id)
        return {"star_id": star_id}

    return await submit(services, JobKind.DEEPEN, f"star:{star_id}:depth", work, {"star_id": star_id}, label=f"deepening of {name}")
