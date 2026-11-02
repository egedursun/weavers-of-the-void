from aerona.agents.chronicler import backfill_chronicles
from aerona.agents.turns.long_jobs import LongJobResult, resolve_orphaned_jobs
from aerona.epoch.context import EpochContext


async def complete_missing(ec: EpochContext) -> None:
    try:
        if ec.hooks.complete_missing is not None:
            await ec.hooks.complete_missing()
            return
        async with ec.database.write() as session:
            rules = await ec.runtime.rules(session)
            resolved = await resolve_orphaned_jobs(session, rules, ec.epoch)
        for job in resolved:
            if job.result is LongJobResult.REFUNDED:
                ec.runtime.note(f"{job.son_name}: the cost of the half-finished birth was refunded.")
        if ec.runtime.llm_enabled:
            await backfill_chronicles(ec.runtime)
    except Exception as error:
        ec.runtime.error(f"Completion: {error}")
