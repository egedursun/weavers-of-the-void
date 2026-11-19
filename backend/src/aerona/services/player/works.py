from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.works import PublicWorksRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.works import WorksStatus
from aerona.engine.works.building import finish_stage
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class WorksTarget(Command):
    works_id: int


@player_action("public_works:advance", ActionKind.EDIT_RECORD)
async def advance_works(scope: PlayerScope, command: WorksTarget) -> Effect:
    ctx = await scope.context("public_works_advance")
    works = await ctx.session.get(PublicWorksRow, command.works_id)
    if works is None:
        raise NotFoundError("No such public works.")
    if works.status is not WorksStatus.BUILDING:
        raise ValidationFailedError("Only works still being built can be carried a stage further.")
    finished = await finish_stage(ctx, works, 0)
    await ctx.session.flush()
    return Effect("The works stand finished." if finished else f"The works reach stage {works.stage} of {works.stages}.")
