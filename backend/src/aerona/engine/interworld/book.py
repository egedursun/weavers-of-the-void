from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interworld import OrbitalControlRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.urban import FleetRow
from aerona.domain.enums.urban import TransportKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import current_calendar, forgotten_world_ids, route_status, touches

CARRYING = frozenset({TransportKind.SPACE, TransportKind.ORBITAL_LIFT, TransportKind.TELEPORT})


@dataclass
class InterworldTally:
    launched: int = 0
    lost_in_transit: int = 0
    orbits_won: int = 0
    orbits_lost: int = 0
    landings: int = 0
    bombardments: int = 0
    withdrawn: int = 0
    migrations: int = 0
    migrants: int = 0
    arrived: int = 0
    refused: int = 0


async def route_open(ctx: TickContext, route: RouteRow) -> bool:
    calendar = await current_calendar(ctx.session, ctx.rules, ctx.epoch)
    return route.active and route_status(route, calendar, await forgotten_world_ids(ctx.session)).is_open


async def route_between(ctx: TickContext, first: int, second: int) -> RouteRow | None:
    query = select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.duration_epochs, RouteRow.id)
    for route in await ctx.session.scalars(query):
        if touches(route, first) and touches(route, second) and first != second and await route_open(ctx, route):
            return route
    return None


async def carriers_of(session: AsyncSession, owner_id: int) -> int:
    query = select(FleetRow.count).where(FleetRow.owner_entity_id == owner_id, FleetRow.kind.in_(sorted(CARRYING)))
    return sum(await session.scalars(query))


async def orbit_of(session: AsyncSession, world_id: int) -> OrbitalControlRow | None:
    return await session.scalar(select(OrbitalControlRow).where(OrbitalControlRow.world_id == world_id).limit(1))
