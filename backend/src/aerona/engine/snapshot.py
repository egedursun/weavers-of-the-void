from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import SINGLETON_ID
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochStatsRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.travel import JourneyStatus
from aerona.domain.models.records import EpochStatsData, LedgerItem, SonEpochStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.leak import leak_breakdown
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.ledger import LedgerKey, doom_items, essence_items, has, read
from aerona.engine.primitives.queries import canon, flags_by_entity, living_sons
from aerona.engine.primitives.stats import stat

POPULATION_ENGINE = "war, disasters, migration and births (engine)"
POPULATION_CLIMATE = "climate"
POPULATION_GROWTH = "logistic growth"
POPULATION_CULTS = "joined cults"


async def _count(session: AsyncSession, entity_type: EntityType) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == entity_type)
    return int(await session.scalar(statement) or 0)


async def _bond_count(session: AsyncSession, kind: BondKind) -> int:
    statement = select(func.count()).select_from(BondRow).where(BondRow.kind == kind, BondRow.state == BondState.ACTIVE)
    return int(await session.scalar(statement) or 0)


TRAVELLING = (JourneyStatus.UNDERWAY, JourneyStatus.WAITING, JourneyStatus.STRANDED)


async def world_snapshot(session: AsyncSession) -> EpochStatsData:
    land = await canon(session, [EntityType.PEOPLE, EntityType.SETTLEMENT])
    cults = await canon(session, [EntityType.CULT])
    godless = await flags_by_entity(session, EntityFlag.GODLESS)
    canon_ids = set(await session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    sons = {son.id: SonEpochStats(faith=son.faith, fame=son.fame, existence=son.existence, level=son.level) for son in await living_sons(session)}
    return EpochStatsData(
        population=sum(stat(community, "population") or 0 for community in land),
        followers=sum(stat(cult, "followers") or 0 for cult in cults),
        entities=len(canon_ids),
        words=int(await session.scalar(select(func.count()).select_from(LexemeRow)) or 0),
        knowledge=await _count(session, EntityType.KNOWLEDGE),
        languages=await _count(session, EntityType.LANGUAGE),
        wars=await _bond_count(session, BondKind.ENEMY),
        trade_routes=await _bond_count(session, BondKind.TRADES_WITH),
        alliances=await _bond_count(session, BondKind.ALLY),
        structures=await _count(session, EntityType.STRUCTURE),
        items=await _count(session, EntityType.ITEM),
        dead=int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.DEAD)) or 0),
        godless=len(godless & canon_ids),
        doom=await current_doom(session),
        sons=sons,
        soldiers=sum(stat(army, "size") or 0 for army in await canon(session, [EntityType.ARMY])),
        travelling=int(await session.scalar(select(func.coalesce(func.sum(JourneyRow.population), 0)).where(JourneyRow.status.in_(TRAVELLING))) or 0),
    )


def item_pairs(items: tuple[LedgerItem, ...]) -> list[tuple[str, int]]:
    return [(item.item, round(item.delta)) for item in items]


def flow_summary(flows: Counter[tuple[str, str, int, str]]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for (_, key, _, category), delta in flows.items():
        totals[f"{category}.{key}"] += delta
    return dict(totals)


async def store_tick_flows(session: AsyncSession, epoch: int, flows: Counter[tuple[str, str, int, str]]) -> None:
    row = await session.get(EpochStatsRow, epoch)
    summary = _items(flow_summary(flows))
    if row is None:
        session.add(EpochStatsRow(epoch=epoch, data=EpochStatsData(flow_items=summary)))
    else:
        row.data = row.data.model_copy(update={"flow_items": summary})
    await session.flush()


def _items(values: dict[str, int]) -> tuple[LedgerItem, ...]:
    return tuple(LedgerItem(item=label, delta=round(delta)) for label, delta in values.items() if round(delta) != 0)


async def previous_population(session: AsyncSession, epoch: int) -> int | None:
    row: EpochStatsRow | None = await session.scalar(select(EpochStatsRow).where(EpochStatsRow.epoch < epoch).order_by(EpochStatsRow.epoch.desc()).limit(1))
    return row.data.population if row is not None else None


async def population_items(ctx: TickContext) -> dict[str, int]:
    if not has(ctx, LedgerKey.POPULATION_START):
        return {}
    start = read(ctx, LedgerKey.POPULATION_START)
    previous = await previous_population(ctx.session, ctx.epoch)
    items = {
        POPULATION_CLIMATE: read(ctx, LedgerKey.POPULATION_BEFORE_GROWTH) - start if has(ctx, LedgerKey.POPULATION_BEFORE_GROWTH) else 0,
        POPULATION_GROWTH: read(ctx, LedgerKey.POPULATION_GROWTH),
        POPULATION_CULTS: -read(ctx, LedgerKey.POPULATION_TO_CULTS),
    }
    if previous is not None:
        items = {POPULATION_ENGINE: start - previous, **items}
    return items


async def current_doom(session: AsyncSession) -> int:
    cosmos = await session.get(CosmosRow, SINGLETON_ID)
    return cosmos.doom_clock if cosmos is not None else 0


async def epoch_statistics(ctx: TickContext) -> EpochStatsData:
    snapshot = await world_snapshot(ctx.session)
    data = snapshot.model_copy(
        update={
            "doom": read(ctx, LedgerKey.DOOM_CLOCK) if has(ctx, LedgerKey.DOOM_CLOCK) else await current_doom(ctx.session),
            "doom_items": _items({item.value: delta for item, delta in doom_items(ctx).items()}),
            "leak_items": await leak_breakdown(ctx.session, ctx.epoch),
            "population_items": _items(await population_items(ctx)),
            "essence_items": _items({item.value: delta for item, delta in essence_items(ctx).items()}),
        }
    )
    row = await ctx.session.get(EpochStatsRow, ctx.epoch)
    earlier = dict(item_pairs(row.data.flow_items)) if row is not None else {}
    for key, delta in flow_summary(ctx.environment.stats.flows).items():
        earlier[key] = earlier.get(key, 0) + delta
    data = data.model_copy(update={"flow_items": _items(earlier)})
    if row is None:
        ctx.session.add(EpochStatsRow(epoch=ctx.epoch, data=data))
    else:
        row.data = data
    await ctx.session.flush()
    return data


@reads(
    "army.size",
    "cult.followers",
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.cosmos",
    "table.entity_flags",
    "table.epoch_stats",
    "table.journeys",
    "table.lexemes",
    "table.world_leak_items",
)
@writes("table.epoch_stats")
async def record_statistics(ctx: TickContext) -> None:
    await epoch_statistics(ctx)


PHASES = (Phase("epoch_statistics", record_statistics),)
