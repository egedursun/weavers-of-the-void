from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.engine.context import Publisher, TickContext
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.cosmos.routes import connect_all_worlds
from aerona.engine.cosmos.worlds import align_moons, pair_mirrors
from aerona.engine.phases.exploration import recover_intuitions
from aerona.engine.pipeline import current_environment
from aerona.engine.primitives.manual import silent

StartupStep = Callable[[TickContext], Awaitable[int]]


async def mirrors_paired(ctx: TickContext) -> int:
    return await pair_mirrors(ctx.session)


async def moons_aligned(ctx: TickContext) -> int:
    return await align_moons(ctx.session)


async def intuitions_recovered(ctx: TickContext) -> int:
    return await recover_intuitions(ctx.session)


async def worlds_connected(ctx: TickContext) -> int:
    return await connect_all_worlds(ctx)


async def maps_drawn(ctx: TickContext) -> int:
    return len(await refresh_world_maps(ctx.session, ctx.rules, ctx.epoch))


STARTUP_STEPS: tuple[tuple[str, StartupStep], ...] = (
    ("pair_mirrors", mirrors_paired),
    ("align_moons", moons_aligned),
    ("recover_intuitions", intuitions_recovered),
    ("connect_all_worlds", worlds_connected),
    ("world_maps", maps_drawn),
)


@dataclass(frozen=True)
class StartupReport:
    ran: bool
    changes: dict[str, int] = field(default_factory=dict)


async def cosmos_exists(database: Database) -> bool:
    async with database.read() as session:
        return await CosmosRepository(session).get() is not None


async def prepare_engine(database: Database, publish: Publisher = silent) -> StartupReport:
    if not await cosmos_exists(database):
        return StartupReport(ran=False)
    environment = await current_environment(database, publish)
    changes: dict[str, int] = {}
    for name, step in STARTUP_STEPS:
        async with database.write() as session:
            changes[name] = await step(TickContext(environment, session, f"startup.{name}"))
    return StartupReport(ran=True, changes=changes)
