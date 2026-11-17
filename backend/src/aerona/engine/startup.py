from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.engine.context import Publisher, TickContext
from aerona.engine.cosmos.maps import refresh_world_maps
from aerona.engine.cosmos.routes import connect_all_worlds
from aerona.engine.cosmos.worlds import align_moons, pair_mirrors
from aerona.engine.economy.good_kinds import ensure_built_in_goods
from aerona.engine.households.dwelling_kinds import ensure_built_in_dwellings
from aerona.engine.kinds.culture_life import ensure_culture_built_ins
from aerona.engine.kinds.nature import ensure_built_ins as ensure_nature_built_ins
from aerona.engine.kinds.society import ensure_built_ins as ensure_society_built_ins
from aerona.engine.phases.exploration import recover_intuitions
from aerona.engine.pipeline import current_environment
from aerona.engine.primitives.manual import silent
from aerona.engine.recording.checkpoints import first_checkpoint
from aerona.engine.recording.legacy import upgrade_records

StartupStep = Callable[[TickContext], Awaitable[int]]


async def mirrors_paired(ctx: TickContext) -> int:
    return await pair_mirrors(ctx.session)


async def moons_aligned(ctx: TickContext) -> int:
    return await align_moons(ctx.session)


async def intuitions_recovered(ctx: TickContext) -> int:
    return await recover_intuitions(ctx.session)


async def worlds_connected(ctx: TickContext) -> int:
    return await connect_all_worlds(ctx)


async def dwellings_built_in(ctx: TickContext) -> int:
    return await ensure_built_in_dwellings(ctx.session)


async def kinds_built_in(ctx: TickContext) -> int:
    session = ctx.session
    made = await ensure_built_in_goods(session) + await ensure_nature_built_ins(session)
    return made + await ensure_society_built_ins(session) + await ensure_culture_built_ins(session)


async def maps_drawn(ctx: TickContext) -> int:
    return len(await refresh_world_maps(ctx.session, ctx.rules, ctx.epoch))


async def records_upgraded(ctx: TickContext) -> int:
    return await upgrade_records(ctx.session)


async def checkpoint_taken(ctx: TickContext) -> int:
    return await first_checkpoint(ctx.session, ctx.epoch)


STARTUP_STEPS: tuple[tuple[str, StartupStep], ...] = (
    ("pair_mirrors", mirrors_paired),
    ("align_moons", moons_aligned),
    ("recover_intuitions", intuitions_recovered),
    ("connect_all_worlds", worlds_connected),
    ("world_maps", maps_drawn),
    ("built_in_dwellings", dwellings_built_in),
    ("built_in_kinds", kinds_built_in),
    ("legacy_records", records_upgraded),
    ("first_checkpoint", checkpoint_taken),
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
