from sqlalchemy import select

from aerona.agents.fallen import run_fallen_turn
from aerona.agents.son import run_son_turn
from aerona.agents.son_state import initiative, turn_order
from aerona.core.grammar import several
from aerona.core.random import SeededRandom
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.son import SonStatus
from aerona.epoch.concurrency import pool
from aerona.epoch.context import EpochContext
from aerona.epoch.state import require_run
from aerona.events.kinds import EventKind

INITIATIVE_STREAM = "epoch.initiative"
TURNING = (SonStatus.ACTIVE, SonStatus.FALLEN)


def takes_turn(son: SonRow) -> bool:
    return son.status is SonStatus.ACTIVE or (son.status is SonStatus.FALLEN and son.body_entity_id is not None)


async def turn_of(ec: EpochContext, son: SonRow) -> None:
    if son.status is SonStatus.FALLEN:
        await run_fallen_turn(ec.runtime, son.id)
    else:
        await run_son_turn(ec.runtime, son.id)


async def eligible_sons(ec: EpochContext) -> list[tuple[SonRow, float]]:
    async with ec.database.read() as session:
        rules = await ec.runtime.rules(session)
        cosmos = await CosmosRepository(session).require_cosmos()
        rng = SeededRandom.for_epoch(cosmos.rng_seed, ec.epoch, INITIATIVE_STREAM)
        sons = await session.scalars(
            select(SonRow).where(SonRow.status.in_(TURNING), SonRow.chained.is_(False), SonRow.last_acted_epoch < ec.epoch).order_by(SonRow.id)
        )
        ordered = [(son, initiative(rules, son, rng)) for son in sons if takes_turn(son)]
    return turn_order(ordered)


async def still_due(ec: EpochContext, son_id: int) -> bool:
    async with ec.database.read() as session:
        son = await session.get(SonRow, son_id)
        return son is not None and takes_turn(son) and son.last_acted_epoch < ec.epoch and not son.chained


async def son_turns(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        done = (await require_run(session, ec.epoch)).phase >= EpochPhase.GODS
    if done:
        return
    order = await eligible_sons(ec) if ec.runtime.llm_enabled else []
    ec.publish(EventKind.EPOCH_STARTED, {"order": [{"id": son.id, "name": son.name, "ini": round(value)} for son, value in order], "resuming": ec.resuming})
    await ec.enter_phase(EpochPhase.GODS, f"{several(len(order), 'son', 'sons')}")
    rules = await ec.rules()
    dropped: list[SonRow] = []
    counter = iter(range(1, len(order) + 1))

    async def one(son: SonRow) -> None:
        ec.publish(
            EventKind.SON_TURN_QUEUED,
            {"no": next(counter), "total": len(order), "son_id": son.id, "name": son.name, "model": ec.runtime.world_model, "rarity": son.rarity.value},
        )
        try:
            await turn_of(ec, son)
        except Exception as error:
            dropped.append(son)
            ec.runtime.error(f"{son.name}: {error} — will be retried once at the end of the phase.", retryable=True, son_id=son.id)

    await pool([son for son, _ in order], rules.agents.sons_parallel, one, ec.stop)
    ec.checkpoint(int(EpochPhase.NOT_STARTED))
    for son in dropped:
        ec.checkpoint(int(EpochPhase.NOT_STARTED))
        if not await still_due(ec, son.id):
            continue
        ec.publish(EventKind.AGENT_RETRY, {"actor": son.name, "kind": "dropped_turn", "attempt": 2, "total": 2, "wait_s": 0, "kept_steps": 0})
        try:
            await turn_of(ec, son)
        except Exception as error:
            ec.runtime.error(f"{son.name} could not act this epoch: {error}", son_id=son.id)
    await ec.complete_phase(EpochPhase.GODS)
    ec.checkpoint(int(EpochPhase.GODS))
