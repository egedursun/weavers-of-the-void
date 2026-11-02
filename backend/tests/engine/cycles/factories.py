from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.meta import MapSnapshotRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.war import WarCause, WarEnding, WarStatus
from aerona.domain.models.entity_stats import EventStats
from aerona.domain.models.records import MapSnapshotData
from aerona.engine.context import TickContext, TickEnvironment
from aerona.engine.stats import TickStats
from aerona.rules.registry import Rules
from tests.engine.core.factories import WORLD_SEED, CoreWorld, entity


def tune(rules: Rules, **namespaces: dict[str, int]) -> Rules:
    for namespace, values in namespaces.items():
        rules = replace(rules, **{namespace: replace(getattr(rules, namespace), **values)})
    return rules


def context(session: AsyncSession, world: CoreWorld, rules: Rules, epoch: int) -> TickContext:
    world.cosmos.epoch = epoch
    environment = TickEnvironment(
        rules=rules, epoch=epoch, world_seed=WORLD_SEED, lore_language=world.cosmos.lore_language, publish=lambda kind, payload: None, stats=TickStats()
    )
    return TickContext(environment, session, "test")


async def snapshot(session: AsyncSession, world: CoreWorld, epoch: int, population: dict[int, int]) -> None:
    session.add(MapSnapshotRow(epoch=epoch, world_id=world.world.id, data=MapSnapshotData(population=population)))
    await session.flush()


async def event(
    session: AsyncSession, world: CoreWorld, name: str, kind: EngineKind, *, severity: int = 50, birth_epoch: int = 1, location_id: int | None = None
) -> EntityRow:
    row = await entity(
        session, name, EntityType.EVENT, EventStats(severity=severity), world_id=world.world.id, birth_epoch=birth_epoch, location_id=location_id
    )
    row.engine_kind = kind
    await session.flush()
    return row


async def war(
    session: AsyncSession, world: CoreWorld, first: EntityRow, second: EntityRow, *, ended: int | None = None, victor: EntityRow | None = None
) -> WarRow:
    record = await event(session, world, f"War of {first.name} and {second.name}", EngineKind.WAR)
    row = WarRow(
        event_entity_id=record.id,
        world_id=world.world.id,
        status=WarStatus.ENDED if ended is not None else WarStatus.ONGOING,
        cause=WarCause.HOSTILITY,
        started_epoch=1,
        ended_epoch=ended,
        battles=4,
        ending=(WarEnding.VICTORY if victor is not None else WarEnding.WHITE_PEACE) if ended is not None else None,
        victor_entity_id=victor.id if victor is not None else None,
        loser_entity_id=(second.id if victor is first else first.id) if victor is not None else None,
    )
    session.add(row)
    await session.flush()
    return row


async def flags(session: AsyncSession, entity_id: int) -> set[str]:
    return {flag.value for flag in await EntityRepository(session).flags(entity_id)}
