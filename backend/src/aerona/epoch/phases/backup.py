from aerona.domain.enums.epoch import EpochStepKind, EpochStepStatus
from aerona.epoch.context import EpochContext
from aerona.epoch.state import require_run
from aerona.events.kinds import EventKind

BACKUP_LABEL = "epoch{epoch}"


async def take_backup(ec: EpochContext) -> None:
    async with ec.database.read() as session:
        run = await require_run(session, ec.epoch)
        started = run.started
    if started:
        return
    if ec.hooks.backup is None:
        await ec.mark(EpochStepKind.BACKUP, EpochStepStatus.SKIPPED)
    else:
        try:
            name = await ec.hooks.backup(BACKUP_LABEL.format(epoch=ec.epoch))
            ec.runtime.note(f"A backup of the world was taken before Epoch {ec.epoch} started ({name}).")
            ec.publish(EventKind.EPOCH_BACKUP, {"file": name})
            await ec.mark(EpochStepKind.BACKUP, EpochStepStatus.DONE)
        except Exception as error:
            ec.runtime.error(f"Backup could not be taken: {error}")
            await ec.mark(EpochStepKind.BACKUP, EpochStepStatus.FAILED, str(error))
    async with ec.database.write() as session:
        (await require_run(session, ec.epoch)).started = True
