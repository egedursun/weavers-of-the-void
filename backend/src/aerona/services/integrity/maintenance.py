import asyncio
from dataclasses import dataclass, field

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.engine.context import Publisher
from aerona.events.bus import EventBus
from aerona.rules.registry import Rules
from aerona.services.bonds import BondService
from aerona.services.chronicle import ChronicleWriter
from aerona.services.integrity.data_repairs import GRAPH_ENDS_STEP, SCHEMA_STEP, DataRepairs, history_signed, sign_history
from aerona.services.integrity.network import RepairLog, RepairLogEntry
from aerona.services.notifications import Notifier

HISTORY_STEP = "history_repairs"


@dataclass(frozen=True)
class Maintained:
    counters: dict[str, int]
    log: list[RepairLogEntry] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)


async def repair_steps(repairs: DataRepairs, database: Database, rules: Rules, *, force_history: bool = False) -> dict[str, int]:
    async with database.read() as session:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            return {}
        epoch = cosmos.epoch
        history = force_history or not await history_signed(session)
    steps = [step for step in repairs.startup_steps() if step[0] != GRAPH_ENDS_STEP] + (repairs.history_steps() if history else [])
    counters: dict[str, int] = {}
    for name, step in steps:
        async with database.write() as session:
            counters[name] = await step(session, rules, epoch)
        await asyncio.sleep(0)
    if history:
        async with database.write() as session:
            await sign_history(session)
        counters[HISTORY_STEP] = 1
    return counters


async def graph_ends(repairs: DataRepairs, database: Database, rules: Rules) -> int:
    async with database.read() as session:
        cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return 0
    async with database.write() as session:
        return await repairs.graph_ends(session, rules, cosmos.epoch)


async def schema(repairs: DataRepairs, database: Database, rules: Rules) -> int:
    async with database.write() as session:
        return await repairs.schema(session, rules, 0)


def repairs_for(publish: Publisher) -> tuple[DataRepairs, RepairLog]:
    bus = EventBus()
    bus.add_listener(lambda event: publish(event.kind, event.payload))
    log = RepairLog()
    return DataRepairs(BondService(ChronicleWriter(Notifier(bus))), log), log


async def startup_repairs(database: Database, publish: Publisher, rules: Rules) -> Maintained:
    repairs, log = repairs_for(publish)
    counters = await repair_steps(repairs, database, rules)
    return Maintained(counters, log.recent(rules.link_graph.summary_list))


async def background_repairs(database: Database, publish: Publisher, rules: Rules) -> Maintained:
    repairs, log = repairs_for(publish)
    counters: dict[str, int] = {}
    failures: dict[str, str] = {}
    for name, repair in ((GRAPH_ENDS_STEP, graph_ends), (SCHEMA_STEP, schema)):
        try:
            counters[name] = await repair(repairs, database, rules)
        except Exception as error:
            counters[name] = 0
            failures[name] = f"{type(error).__name__}: {error}"
    return Maintained(counters, log.recent(rules.link_graph.summary_list), failures)
