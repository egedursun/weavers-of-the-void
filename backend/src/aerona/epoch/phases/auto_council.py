from sqlalchemy import select

from aerona.agents.council import convene_council
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.epochs import DeferredStepRow
from aerona.domain.enums.agent import CouncilCaller
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EpochPhase, EpochStepKind, EpochStepStatus
from aerona.engine.divine.rulings import engine_council
from aerona.engine.primitives.manual import manual_context
from aerona.epoch.context import EpochContext
from aerona.epoch.state import attempted


async def council_due(ec: EpochContext) -> bool:
    async with ec.database.read() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = await ec.runtime.rules(session)
        frequency = cosmos.council_every_epochs if cosmos.council_every_epochs is not None else rules.council.default_interval
        return frequency > 0 and ec.epoch % frequency == 0 and not await attempted(session, ec.epoch, EpochStepKind.COUNCIL)


async def auto_council(ec: EpochContext) -> None:
    if not await council_due(ec):
        return
    if not ec.runtime.llm_enabled:
        async with ec.database.write() as session:
            rules = await ec.runtime.rules(session)
            held_council = await engine_council(await manual_context(session, "engine_council", rules, key=str(ec.epoch)))
        if held_council is None:
            await ec.mark(EpochStepKind.COUNCIL, EpochStepStatus.SKIPPED)
            return
        ec.summary["council"] = held_council.topic
        await ec.mark(EpochStepKind.COUNCIL, EpochStepStatus.DONE)
        return
    async with ec.database.write() as session:
        step = await session.scalar(select(DeferredStepRow).where(DeferredStepRow.epoch == ec.epoch, DeferredStepRow.kind == DeferredStepKind.COUNCIL))
        if step is None:
            step = DeferredStepRow(epoch=ec.epoch, kind=DeferredStepKind.COUNCIL, status=DeferredStepStatus.RUNNING, attempts=1)
            session.add(step)
        await session.flush()
        step_id = step.id
    await ec.mark(EpochStepKind.COUNCIL, EpochStepStatus.RUNNING)
    try:
        result = await convene_council(ec.runtime, caller=CouncilCaller.FATE)
        status, error = DeferredStepStatus.DONE, None
        ec.summary["council"] = result.motion
        await ec.mark(EpochStepKind.COUNCIL, EpochStepStatus.DONE)
    except Exception as failure:
        status, error = DeferredStepStatus.FAILED, str(failure)
        await ec.mark(EpochStepKind.COUNCIL, EpochStepStatus.FAILED, error)
        ec.runtime.error(f"Council: {failure}")
    async with ec.database.write() as session:
        row = await session.get(DeferredStepRow, step_id)
        if row is not None:
            row.status = status
            row.error = error
    ec.checkpoint(int(EpochPhase.ENGINE))
