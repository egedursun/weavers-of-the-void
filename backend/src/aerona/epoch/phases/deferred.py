from functools import partial

from sqlalchemy import func, select

from aerona.agents.bard import write_son_epic
from aerona.agents.deepener import creator_deepen, creator_epic, deepen_entity, deepen_foreign_god, refresh_awakened_god
from aerona.agents.network_repair import network_fate_repair
from aerona.agents.world_birth import process_deferred_births, process_intuitions
from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.types import json_missing
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.epoch import EpochStepKind, EpochStepStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus
from aerona.engine.prehistory.run import born_prehistories
from aerona.epoch.context import EpochContext
from aerona.epoch.phases.naming import name_pending
from aerona.epoch.state import attempted, step_status

DEEPENABLE_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.FULFILLED)
CREATOR_EPIC_KEY = "creator:epic"
CREATOR_DEPTH_KEY = "creator:depth"


async def deferred_worlds(ec: EpochContext) -> None:
    if not ec.runtime.llm_enabled:
        return
    async with ec.database.read() as session:
        status = await step_status(session, ec.epoch, EpochStepKind.WORLD_BIRTH)
    if status is not None and status is not EpochStepStatus.RUNNING:
        await name_pending(ec)
        return
    await ec.mark(EpochStepKind.WORLD_BIRTH, EpochStepStatus.RUNNING)
    try:
        born = await process_intuitions(ec.runtime) + await process_deferred_births(ec.runtime)
        ec.summary["worlds_born"] = born
        ec.summary["prehistories"] = await born_prehistories(ec.database, ec.epoch, publish=ec.publish)
        await ec.mark(EpochStepKind.WORLD_BIRTH, EpochStepStatus.DONE)
    except Exception as error:
        await ec.mark(EpochStepKind.WORLD_BIRTH, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Sensed worlds: {error}")
    await name_pending(ec)


async def auto_deepen_candidates(ec: EpochContext, count: int) -> list[int]:
    async with ec.database.read() as session:
        rules = await ec.runtime.rules(session)
        degree = (
            select(func.count())
            .select_from(BondRow)
            .where(BondRow.state == BondState.ACTIVE, (BondRow.source_node_id == EntityRow.id) | (BondRow.target_node_id == EntityRow.id))
            .correlate(EntityRow)
            .scalar_subquery()
        )
        statement = (
            select(EntityRow.id)
            .where(json_missing(EntityRow.depth), EntityRow.status.in_(DEEPENABLE_STATUSES))
            .order_by(
                EntityRow.pending_name,
                func.coalesce(EntityRow.importance, 0).desc(),
                (degree + EntityRow.power_level * rules.agents.auto_deepen_power_weight).desc(),
                EntityRow.id,
            )
            .limit(count)
        )
        return list(await session.scalars(statement))


async def stale_epics(ec: EpochContext) -> list[tuple[str, int, int | None]]:
    async with ec.database.read() as session:
        rules = await ec.runtime.rules(session)
        threshold = rules.agents.epic_refresh_epochs
        if threshold <= 0:
            return []
        creator = await CosmosRepository(session).require_creator()
        found: list[tuple[str, int, int | None]] = []
        if creator.epic is not None:
            found.append((CREATOR_EPIC_KEY, creator.epic.epoch, None))
        if creator.depth is not None:
            found.append((CREATOR_DEPTH_KEY, creator.depth.epoch, None))
        for son in await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD, SonRow.epic.is_not(None))):
            if son.epic is not None:
                found.append((f"son:{son.id}:epic", son.epic.epoch, son.id))
        due = [item for item in found if ec.epoch - item[1] >= threshold]
        return sorted(due, key=lambda item: item[1])[: rules.agents.epic_refresh_per_epoch]


async def launch_background(ec: EpochContext) -> None:
    spawn = ec.hooks.spawn
    if spawn is None or not ec.runtime.llm_enabled:
        return
    async with ec.database.read() as session:
        if await attempted(session, ec.epoch, EpochStepKind.BACKGROUND):
            return
        rules = await ec.runtime.rules(session)
        gods = list(await session.scalars(select(ForeignGodRow.id).where(json_missing(ForeignGodRow.depth)).order_by(ForeignGodRow.id)))
        woken = list(
            await session.scalars(select(ForeignGodRow.id).where(ForeignGodRow.id.in_(ec.sleeping_gods), ForeignGodRow.status == ForeignGodStatus.AWAKE))
        )
    runtime = ec.runtime
    for god_id in woken:
        spawn(f"foreign:{god_id}:awakened", partial(refresh_awakened_god, runtime, god_id))
    if rules.agents.auto_deepen > 0:
        for god_id in [god for god in gods if god not in woken]:
            spawn(f"foreign:{god_id}:depth", partial(deepen_foreign_god, runtime, god_id))
        ids = await auto_deepen_candidates(ec, rules.agents.auto_deepen)
        started = [entity_id for entity_id in ids if spawn(f"entity:{entity_id}:depth", partial(deepen_entity, runtime, entity_id))]
        if started:
            runtime.note(f"The epoch's {len(started)} most important records are being deepened in the background.")
    refreshed = 0
    room = ec.hooks.spare() if ec.hooks.spare is not None else len(await stale_epics(ec))
    for key, _, son_id in (await stale_epics(ec))[: max(0, room)]:
        if key == CREATOR_EPIC_KEY:
            refreshed += spawn(key, partial(creator_epic, runtime))
        elif key == CREATOR_DEPTH_KEY:
            refreshed += spawn(key, partial(creator_deepen, runtime))
        elif son_id is not None:
            refreshed += spawn(key, partial(write_son_epic, runtime, son_id))
    if refreshed:
        runtime.note(f"{several(refreshed, 'outdated epic is', 'outdated epics are')} being rewritten in the background.")
    if rules.link_graph.fate_auto:
        spawn("network:fate", partial(network_fate_repair, runtime, automatic=True))
    await ec.mark(EpochStepKind.BACKGROUND, EpochStepStatus.DONE)
