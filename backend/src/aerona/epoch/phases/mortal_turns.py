from sqlalchemy import delete, select

from aerona.agents.context.scope import load_scope
from aerona.agents.mortal import choose_mortal_agents, run_mortal_turn
from aerona.db.tables.agency import EpochAgentRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.epoch import EpochPhase
from aerona.epoch.concurrency import pool
from aerona.epoch.context import EpochContext
from aerona.epoch.state import require_run
from aerona.events.kinds import EventKind


async def chosen_agents(ec: EpochContext, count: int) -> list[int]:
    async with ec.database.write() as session:
        rows = list(await session.scalars(select(EpochAgentRow).where(EpochAgentRow.epoch == ec.epoch).order_by(EpochAgentRow.position)))
        if rows:
            return [row.entity_id for row in rows]
        scope = await load_scope(session, await ec.runtime.rules(session))
        picked = await choose_mortal_agents(scope, count)
        await session.execute(delete(EpochAgentRow).where(EpochAgentRow.epoch == ec.epoch))
        session.add_all(EpochAgentRow(epoch=ec.epoch, entity_id=entity.id, position=index, world_id=entity.world_id) for index, entity in enumerate(picked))
        return [entity.id for entity in picked]


async def due_agents(ec: EpochContext, ids: list[int]) -> list[EntityRow]:
    async with ec.database.read() as session:
        rows = [await session.get(EntityRow, entity_id) for entity_id in ids]
    return [row for row in rows if row is not None and row.status is EntityStatus.CANON and row.last_acted_epoch < ec.epoch]


async def mortal_turns(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        run = await require_run(session, ec.epoch)
        scope = await load_scope(session, await ec.runtime.rules(session))
        done = run.phase >= EpochPhase.MORTALS
        count = scope.cosmos.mortal_agents_per_epoch if scope.cosmos.mortal_agents_per_epoch is not None else scope.rules.mortal_agents.agents_per_epoch
        parallel = scope.cosmos.mortal_agent_parallelism or 1
    if done:
        return
    if count > 0 and ec.runtime.llm_enabled:
        agents = await due_agents(ec, await chosen_agents(ec, count))
        await ec.enter_phase(EpochPhase.MORTALS, str(len(agents)))
        ec.publish(EventKind.MORTALS_STARTED, {"agents": [{"id": agent.id, "name": agent.name, "type": agent.entity_type.value} for agent in agents]})

        positions = {agent.id: (index + 1, len(agents)) for index, agent in enumerate(agents)}

        async def one(agent: EntityRow) -> None:
            try:
                await run_mortal_turn(ec.runtime, agent.id, positions[agent.id])
            except Exception as error:
                ec.runtime.error(f"{agent.name}: {error} — retrying once.", retryable=True)
                try:
                    await run_mortal_turn(ec.runtime, agent.id, positions[agent.id])
                except Exception as second:
                    ec.runtime.error(f"{agent.name} could not act this epoch: {second}")

        await pool(agents, parallel, one, ec.stop)
    ec.checkpoint(int(EpochPhase.GODS))
    await ec.complete_phase(EpochPhase.MORTALS)
