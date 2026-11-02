from aerona.agents.localiser import localise_epoch
from aerona.domain.enums.epoch import EpochStepKind, EpochStepStatus
from aerona.epoch.context import EpochContext
from aerona.epoch.state import attempted, finish_run
from aerona.events.kinds import EventKind


async def network_rule_repair(ec: EpochContext) -> None:
    rules = await ec.rules()
    hook = ec.hooks.network_rule_repair
    async with ec.database.read() as session:
        if await attempted(session, ec.epoch, EpochStepKind.NETWORK_REPAIR):
            return
    if hook is None or not rules.link_graph.auto_repair:
        await ec.mark(EpochStepKind.NETWORK_REPAIR, EpochStepStatus.SKIPPED)
        return
    try:
        await hook(ec.epoch)
        await ec.mark(EpochStepKind.NETWORK_REPAIR, EpochStepStatus.DONE)
    except Exception as error:
        await ec.mark(EpochStepKind.NETWORK_REPAIR, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Network repair: {error}")


async def prune(ec: EpochContext) -> None:
    hook = ec.hooks.prune
    if hook is None:
        await ec.mark(EpochStepKind.PRUNE, EpochStepStatus.SKIPPED)
        return
    try:
        async with ec.database.write() as session:
            await hook(session, await ec.runtime.rules(session), ec.epoch)
        await ec.mark(EpochStepKind.PRUNE, EpochStepStatus.DONE)
    except Exception as error:
        await ec.mark(EpochStepKind.PRUNE, EpochStepStatus.FAILED, str(error))


async def close_epoch(ec: EpochContext) -> None:
    async with ec.database.write() as session:
        await finish_run(session, ec.epoch)
    duration = round(ec.elapsed())
    ec.summary["duration_s"] = duration
    ec.publish(EventKind.EPOCH_FINISHED, {"new_epoch": ec.epoch + 1, "summary": ec.summary, "duration_s": duration})
    if ec.hooks.after_epoch is not None:
        try:
            await ec.hooks.after_epoch(ec.epoch)
        except Exception as error:
            ec.runtime.error(f"After the epoch: {error}")


async def localise(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        if await attempted(session, ec.epoch, EpochStepKind.LOCALISATION):
            return
    if not ec.runtime.llm_enabled:
        await ec.mark(EpochStepKind.LOCALISATION, EpochStepStatus.SKIPPED)
        return
    try:
        count = await localise_epoch(ec.runtime, ec.epoch)
        await ec.mark(EpochStepKind.LOCALISATION, EpochStepStatus.DONE)
        ec.summary["localised_lines"] = count
    except Exception as error:
        await ec.mark(EpochStepKind.LOCALISATION, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Localisation: {error}")
