from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.bard import voices_of_peoples
from aerona.agents.chronicle_audit import ChronicleText, review
from aerona.agents.fate.judge import run_fate
from aerona.agents.fate.naming import name_pending_records, pending_count
from aerona.agents.runtime import AgentRuntime
from aerona.agents.world_birth import process_deferred_births, process_intuitions
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import CreationVerdictRow
from aerona.db.tables.epochs import DeferredStepRow, EpochRow, EpochRunRow, EpochWorldNarrativeRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EpochStepKind, EpochStepStatus
from aerona.domain.models.records import ChronicleCoverage
from aerona.epoch.state import mark_step
from aerona.events.kinds import EventKind

NO_RUN = "No epoch has run yet."
NO_DEBT = "Fate carries no debt."
NO_LIMBO = "No creation waits in limbo."
NO_CHRONICLE = "Age {epoch} has no written chronicle to audit."
RETRYABLE_BIRTH_STATUSES = (DeferredStepStatus.FAILED, DeferredStepStatus.RUNNING)


async def last_run(session: AsyncSession) -> EpochRunRow:
    top = await session.scalar(select(func.max(EpochRunRow.epoch)))
    run = await session.get(EpochRunRow, top) if top is not None else None
    if run is None:
        raise ValidationFailedError(NO_RUN)
    return run


async def limbo_epochs(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(CreationVerdictRow.epoch).where(CreationVerdictRow.verdict == Verdict.LIMBO)))


async def retry_fate(runtime: AgentRuntime) -> dict[str, int]:
    runtime.require_llm("retrying Fate")
    async with runtime.database.read() as session:
        run = await last_run(session)
        epoch, notes = run.epoch, list(run.engine_notes)

    async def marker(session: AsyncSession) -> None:
        await mark_step(session, epoch, EpochStepKind.FATE_JUDGMENT, EpochStepStatus.DONE)

    applied = await run_fate(runtime, epoch, notes, marker)
    runtime.publish(EventKind.FATE_FINISHED, {"epoch": epoch, "rejected": applied.rejected, "corrected": applied.fixed, "fate_debt": applied.fate_debt})
    return {"epoch": epoch, "rejected": len(applied.rejected), "fixed": len(applied.fixed), "limbo": len(applied.limbo)}


async def rejudge_debt(runtime: AgentRuntime) -> dict[str, int]:
    async with runtime.database.read() as session:
        if (await CosmosRepository(session).require_cosmos()).fate_debt_epoch is None:
            raise ValidationFailedError(NO_DEBT)
    return await retry_fate(runtime)


async def rejudge_limbo(runtime: AgentRuntime) -> dict[str, int]:
    async with runtime.database.write() as session:
        epochs = await limbo_epochs(session)
        if not epochs:
            raise ValidationFailedError(NO_LIMBO)
        cosmos = await CosmosRepository(session).require_cosmos()
        cosmos.fate_debt_epoch = min([*epochs, *([cosmos.fate_debt_epoch] if cosmos.fate_debt_epoch is not None else [])])
    return await retry_fate(runtime)


async def retry_voices(runtime: AgentRuntime) -> dict[str, int]:
    runtime.require_llm("retrying the voices of the peoples")
    async with runtime.database.read() as session:
        epoch = (await last_run(session)).epoch
    result = await voices_of_peoples(runtime, epoch)
    async with runtime.database.write() as session:
        await mark_step(session, epoch, EpochStepKind.VOICES, EpochStepStatus.DONE)
    return {"epoch": epoch, "views": result.views, "beliefs": result.beliefs}


async def retry_births(runtime: AgentRuntime) -> dict[str, int]:
    runtime.require_llm("retrying the births of sensed worlds")
    async with runtime.database.write() as session:
        epoch = (await last_run(session)).epoch
        steps = await session.scalars(
            select(DeferredStepRow).where(DeferredStepRow.kind == DeferredStepKind.WORLD_BIRTH, DeferredStepRow.status.in_(RETRYABLE_BIRTH_STATUSES))
        )
        for step in steps:
            step.status = DeferredStepStatus.PENDING
            step.error = None
    born = await process_intuitions(runtime) + await process_deferred_births(runtime)
    async with runtime.database.write() as session:
        await mark_step(session, epoch, EpochStepKind.WORLD_BIRTH, EpochStepStatus.DONE)
    async with runtime.database.read() as session:
        waiting = await pending_count(session)
    if waiting:
        await name_pending_records(runtime)
    return {"epoch": epoch, "born": born}


async def audit_epoch_chronicle(runtime: AgentRuntime, epoch: int) -> dict[str, int]:
    async with runtime.database.read() as session:
        row = await session.get(EpochRow, epoch)
        if row is None or not row.narrative:
            raise ValidationFailedError(NO_CHRONICLE.format(epoch=epoch))
        sections = {
            item.world_id: item.narrative or "" for item in await session.scalars(select(EpochWorldNarrativeRow).where(EpochWorldNarrativeRow.epoch == epoch))
        }
        coverage = row.audit.coverage if row.audit is not None else ChronicleCoverage()
        text = ChronicleText(row.narrative, sections)
    repaired, report = await review(runtime, epoch, text, coverage)
    async with runtime.database.write() as session:
        row = await session.get(EpochRow, epoch)
        if row is None:
            raise ValidationFailedError(NO_CHRONICLE.format(epoch=epoch))
        row.narrative = repaired.narrative
        row.audit = report
        for item in await session.scalars(select(EpochWorldNarrativeRow).where(EpochWorldNarrativeRow.epoch == epoch)):
            item.narrative = repaired.sections.get(item.world_id, item.narrative)
    return {
        "epoch": epoch,
        "found": report.found,
        "remaining": len(report.remaining),
        "rewritten": int(report.rewritten),
        "repaired": report.repaired_sentences,
    }
