from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.chronicler import apply_renames, audit_chronicle, complete_chronicle, record_age, write_chronicle
from aerona.agents.context.scope import load_scope
from aerona.agents.fate.judge import run_fate
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.epoch import EpochPhase, EpochStepKind, EpochStepStatus
from aerona.epoch.context import EpochContext
from aerona.epoch.phases.naming import name_pending
from aerona.epoch.state import mark_step, step_settled, step_status
from aerona.events.kinds import EventKind


async def judge(ec: EpochContext) -> list[tuple[str, str]]:
    async def marker(session: AsyncSession) -> None:
        await mark_step(session, ec.epoch, EpochStepKind.FATE_JUDGMENT, EpochStepStatus.DONE)

    try:
        applied = await run_fate(ec.runtime, ec.epoch, ec.engine_notes, marker)
    except Exception as error:
        async with ec.database.write() as session:
            cosmos = await CosmosRepository(session).require_cosmos()
            cosmos.fate_debt_epoch = min(cosmos.fate_debt_epoch, ec.epoch) if cosmos.fate_debt_epoch is not None else ec.epoch
            await mark_step(session, ec.epoch, EpochStepKind.FATE_JUDGMENT, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Fate: {error} — will be compensated next epoch.")
        ec.publish(EventKind.FATE_FINISHED, {"rejected": [], "corrected": []})
        return []
    ec.summary["rejected"] = applied.rejected
    ec.summary["fixed"] = applied.fixed
    ec.publish(EventKind.FATE_FINISHED, {"rejected": applied.rejected, "corrected": applied.fixed, "fate_debt": applied.fate_debt})
    return applied.renamed


async def chronicle(ec: EpochContext, renamed: list[tuple[str, str]]) -> None:
    if not ec.runtime.llm_enabled:
        await ec.mark(EpochStepKind.CHRONICLE, EpochStepStatus.SKIPPED)
        return
    try:
        written = await write_chronicle(ec.runtime, ec.epoch, ec.engine_notes)
        ec.runtime.step(f'The chronicler wrote the age: "{written.age_name}".')
        await complete_chronicle(ec.runtime, written, ec.epoch)
        apply_renames(written, renamed)
        await audit_chronicle(ec.runtime, written, ec.epoch)
        async with ec.database.write() as session:
            rules = await ec.runtime.rules(session)
            row = await record_age(await load_scope(session, rules), written, ec.epoch)
            await mark_step(session, ec.epoch, EpochStepKind.CHRONICLE, EpochStepStatus.DONE)
        ec.summary["epoch_name"] = row.name
    except Exception as error:
        await ec.mark(EpochStepKind.CHRONICLE, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"The chronicler could not write this age ({error}). The missing chronicle will be written at the next completion.")


async def fate_and_chronicle(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        judged = await step_settled(session, ec.epoch, EpochStepKind.FATE_JUDGMENT)
        judged = judged or await step_status(session, ec.epoch, EpochStepKind.FATE_JUDGMENT) is EpochStepStatus.FAILED
        chronicled = await step_settled(session, ec.epoch, EpochStepKind.CHRONICLE)
    if judged and chronicled:
        return
    await ec.enter_phase(EpochPhase.FATE)
    renamed: list[tuple[str, str]] = []
    if not judged:
        ec.publish(EventKind.FATE_STARTED, {})
        await name_pending(ec)
        renamed = await judge(ec)
    if not chronicled:
        await chronicle(ec, renamed)
    ec.checkpoint(int(EpochPhase.ENGINE))
