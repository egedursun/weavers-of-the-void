from aerona.agents.bard import voices_of_peoples
from aerona.domain.enums.epoch import EpochPhase, EpochStepKind, EpochStepStatus
from aerona.epoch.context import EpochContext
from aerona.epoch.state import attempted


async def voices(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        if await attempted(session, ec.epoch, EpochStepKind.VOICES):
            return
    if not ec.runtime.llm_enabled:
        await ec.mark(EpochStepKind.VOICES, EpochStepStatus.SKIPPED)
        return
    await ec.mark(EpochStepKind.VOICES, EpochStepStatus.RUNNING)
    try:
        await voices_of_peoples(ec.runtime, ec.epoch)
        await ec.mark(EpochStepKind.VOICES, EpochStepStatus.DONE)
    except Exception as error:
        await ec.mark(EpochStepKind.VOICES, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Voices of the peoples: {error}")
    ec.checkpoint(int(EpochPhase.ENGINE))
