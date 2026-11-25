from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import shown_lines
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.wars import wars_under_way
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochStatsRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.engine.interconnect.flows import SINKS, FlowCategory
from aerona.engine.interconnect.guards import HEADCOUNT_KEY
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat
from aerona.tools.divine_will.library_ports import FlowDeaths, ForecastLine, ScenarioOutcome, TouchedNode, WarTally

LAND = (EntityType.PEOPLE, EntityType.SETTLEMENT)
PROSPERITY_KEY = "prosperity"
FLOW_SEPARATOR = "."


@dataclass(frozen=True)
class WorldState:
    epoch: int
    population: int
    prosperity: float
    communities: int
    wars: int


def database_at(path: Path) -> Database:
    return Database(f"sqlite+aiosqlite:///{path}")


async def land_figures(session: AsyncSession) -> tuple[int, float]:
    land = await canon(session, list(LAND))
    population = 0
    weighted = 0.0
    counted = 0
    for community in land:
        people = stat(community, HEADCOUNT_KEY) or 0
        population += people
        prosperity = stat(community, PROSPERITY_KEY)
        if prosperity is not None:
            weighted += prosperity * max(1, people)
            counted += max(1, people)
    return population, round(weighted / counted, 2) if counted else 0.0


async def community_count(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    return int(await session.scalar(statement) or 0)


async def current_epoch(session: AsyncSession) -> int:
    return (await CosmosRepository(session).require_cosmos()).epoch


async def world_state(path: Path) -> WorldState:
    database = database_at(path)
    try:
        async with database.read() as session:
            population, prosperity = await land_figures(session)
            return WorldState(await current_epoch(session), population, prosperity, await community_count(session), await wars_under_way(session))
    finally:
        await database.dispose()


async def deaths_since(session: AsyncSession, start_epoch: int) -> list[FlowDeaths]:
    totals: Counter[FlowCategory] = Counter()
    for row in await session.scalars(select(EpochStatsRow).where(EpochStatsRow.epoch >= start_epoch).order_by(EpochStatsRow.epoch)):
        for item in row.data.flow_items:
            category, _, key = item.item.partition(FLOW_SEPARATOR)
            if key != HEADCOUNT_KEY or category not in {sink.value for sink in SINKS} or item.delta >= 0:
                continue
            totals[FlowCategory(category)] += round(-item.delta)
    return [FlowDeaths(category, totals[category]) for category in sorted(totals, key=lambda found: (-totals[found], found.value))]


async def wars_since(session: AsyncSession, start_epoch: int) -> WarTally:
    begun = int(await session.scalar(select(func.count()).select_from(WarRow).where(WarRow.started_epoch >= start_epoch)) or 0)
    ended = int(await session.scalar(select(func.count()).select_from(WarRow).where(WarRow.ended_epoch >= start_epoch)) or 0)
    return WarTally(ongoing=await wars_under_way(session), begun=begun, ended=ended)


async def touched_nodes(session: AsyncSession, node_ids: Sequence[int]) -> list[TouchedNode]:
    found: list[TouchedNode] = []
    for node_id in sorted(set(node_ids)):
        node = await session.get(NodeRow, node_id)
        if node is None:
            found.append(TouchedNode(node_id, "", None, False, None))
            continue
        entity = await session.get(EntityRow, node_id)
        stats = {key: value for key, value in entity.stats.model_dump().items() if isinstance(value, int) and not isinstance(value, bool)} if entity else {}
        found.append(TouchedNode(node_id, node.name, node.kind, True, entity.status if entity else None, stats))
    return found


async def chronicle_since(session: AsyncSession, start_epoch: int) -> list[ForecastLine]:
    rows = await session.execute(
        select(ChronicleRow.epoch, ChronicleRow.year, ChronicleRow.text)
        .where(ChronicleRow.epoch >= start_epoch, shown_lines())
        .order_by(ChronicleRow.epoch, ChronicleRow.year, ChronicleRow.id)
    )
    return [ForecastLine(int(epoch), year, str(text)) for epoch, year, text in rows]


async def scenario(path: Path, start_epoch: int, touched: Sequence[int], seconds: float) -> ScenarioOutcome:
    database = database_at(path)
    try:
        async with database.read() as session:
            population, prosperity = await land_figures(session)
            return ScenarioOutcome(
                population=population,
                prosperity=prosperity,
                communities=await community_count(session),
                deaths=await deaths_since(session, start_epoch),
                wars=await wars_since(session, start_epoch),
                nodes=await touched_nodes(session, touched),
                chronicle=await chronicle_since(session, start_epoch),
                seconds=round(seconds, 2),
            )
    finally:
        await database.dispose()
