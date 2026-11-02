from aerona.domain.enums.epoch import EpochStepKind, EpochStepStatus
from aerona.epoch.context import EpochContext


async def image_autogen(ec: EpochContext) -> None:
    rules = await ec.rules()
    hook = ec.hooks.image_autogen
    if hook is None or not rules.image_gen.auto:
        await ec.mark(EpochStepKind.IMAGES, EpochStepStatus.SKIPPED)
        return
    try:
        await hook()
        await ec.mark(EpochStepKind.IMAGES, EpochStepStatus.DONE)
    except Exception as error:
        await ec.mark(EpochStepKind.IMAGES, EpochStepStatus.FAILED, str(error))
        ec.runtime.error(f"Image generation: {error}")
