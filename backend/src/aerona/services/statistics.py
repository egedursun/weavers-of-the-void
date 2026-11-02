import logging
from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import JSON, select, type_coerce
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.epochs import EpochStatsRow
from aerona.domain.models.records import EpochStatsData, SonEpochStats
from aerona.engine.snapshot import world_snapshot

logger = logging.getLogger(__name__)

NUMERIC_FIELDS = (
    "population",
    "followers",
    "entities",
    "words",
    "knowledge",
    "languages",
    "wars",
    "trade_routes",
    "alliances",
    "structures",
    "items",
    "dead",
    "godless",
    "doom",
)
SON_FIELDS = ("faith", "fame", "existence", "level")


@dataclass(frozen=True)
class EpochStatistics:
    epoch: int
    data: EpochStatsData
    live: bool = False


@dataclass(frozen=True)
class SonDelta:
    son_id: int
    changes: dict[str, int]


@dataclass(frozen=True)
class EpochBreakdown:
    epoch: int
    current: EpochStatsData | None
    previous: EpochStatsData | None
    deltas: dict[str, int] = field(default_factory=dict)
    sons: list[SonDelta] = field(default_factory=list)


async def stored_statistics(session: AsyncSession) -> dict[int, EpochStatsData]:
    rows = await session.execute(select(EpochStatsRow.epoch, type_coerce(EpochStatsRow.data, JSON)).order_by(EpochStatsRow.epoch))
    found: dict[int, EpochStatsData] = {}
    for epoch, raw in rows:
        try:
            found[int(epoch)] = EpochStatsData.model_validate(raw)
        except ValidationError:
            logger.warning("skipping unreadable statistics of epoch %s", epoch)
    return found


async def series(session: AsyncSession) -> list[EpochStatistics]:
    stored = await stored_statistics(session)
    items = [EpochStatistics(epoch, data) for epoch, data in sorted(stored.items())]
    cosmos = await CosmosRepository(session).get()
    if cosmos is not None and cosmos.epoch not in stored:
        items.append(EpochStatistics(cosmos.epoch, await world_snapshot(session), live=True))
    return items


def numeric_deltas(current: EpochStatsData, previous: EpochStatsData | None) -> dict[str, int]:
    return {name: getattr(current, name) - (getattr(previous, name) if previous is not None else 0) for name in NUMERIC_FIELDS}


def son_deltas(current: EpochStatsData, previous: EpochStatsData | None) -> list[SonDelta]:
    deltas: list[SonDelta] = []
    before = previous.sons if previous is not None else {}
    for son_id, stats in sorted(current.sons.items()):
        prior = before.get(son_id, SonEpochStats())
        changes = {name: getattr(stats, name) - getattr(prior, name) for name in SON_FIELDS if getattr(stats, name) != getattr(prior, name)}
        if changes:
            deltas.append(SonDelta(son_id, changes))
    return deltas


async def breakdown(session: AsyncSession, epoch: int) -> EpochBreakdown:
    stored = await stored_statistics(session)
    cosmos = await CosmosRepository(session).get()
    current = stored.get(epoch)
    if current is None and cosmos is not None and epoch == cosmos.epoch:
        current = await world_snapshot(session)
    previous = stored.get(epoch - 1)
    if current is None:
        return EpochBreakdown(epoch=epoch, current=None, previous=previous)
    return EpochBreakdown(epoch, current, previous, numeric_deltas(current, previous), son_deltas(current, previous))


async def pulse(session: AsyncSession) -> EpochStatsData:
    return await world_snapshot(session)
