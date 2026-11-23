from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.disease_agents import AGENT_OF_VECTOR
from aerona.catalog.transmission import DISEASE_ROUTES, ROUTES
from aerona.db.tables.disease import DiseaseProfileRow, DiseaseRouteRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.recording.record import record


async def held_routes(session: AsyncSession, disease_id: int) -> list[Transmission]:
    profile = await session.get(DiseaseProfileRow, disease_id)
    further = await session.scalars(select(DiseaseRouteRow.route).where(DiseaseRouteRow.disease_entity_id == disease_id).order_by(DiseaseRouteRow.route))
    main = [profile.primary_route] if profile is not None else []
    return [*main, *(route for route in further if route not in main)]


def add_route(ctx: TickContext, book: DiseaseBook, disease_id: int, route: Transmission, share: int) -> None:
    ctx.session.add(DiseaseRouteRow(disease_entity_id=disease_id, route=route, share=share, locked=[]))
    book.routes.setdefault(disease_id, []).append((route, share))


def seed_routes(ctx: TickContext, book: DiseaseBook, disease: EntityRow, profile: DiseaseProfileRow) -> None:
    if profile.parent_disease_id is not None:
        for route, share in book.routes.get(profile.parent_disease_id, []):
            add_route(ctx, book, disease.id, route, share)
        return
    table = ctx.rules.transmission
    rng = ctx.rng(f"disease.routes.{disease.id}")
    if not rng.chance(table.further_route_pct):
        return
    agent = AGENT_OF_VECTOR[profile.primary_route]
    kin = [route for route in DISEASE_ROUTES if route is not profile.primary_route and ROUTES[route].agent is agent]
    choices = kin or [route for route in DISEASE_ROUTES if route is not profile.primary_route]
    low, high = sorted((table.further_share_min, table.further_share_max))
    add_route(ctx, book, disease.id, rng.pick(choices), rng.integer(low, high))


async def learn_routes(ctx: TickContext, community: EntityRow, disease_id: int, response: PlagueResponse, *, first: bool) -> None:
    routes = await held_routes(ctx.session, disease_id)
    if first and routes:
        await record(ctx, "disease.route_found", roles={IncidentRole.ACTOR: community.id, IncidentRole.TARGET: disease_id}, facts={"route": routes[0]})
    for route in routes:
        if response in ROUTES[route].blocked_by:
            await record(
                ctx,
                "disease.route_blocked",
                roles={IncidentRole.ACTOR: community.id, IncidentRole.TARGET: disease_id},
                facts={"route": route, "response": response},
            )
