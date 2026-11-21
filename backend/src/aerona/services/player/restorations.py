from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.restoration import RestorationRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.restoration import OPEN_STAGES, RestorationStage
from aerona.engine.restoration.rise import RestorationTally, restore
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NEXT_STAGE = {RestorationStage.MEMORY: RestorationStage.MOVEMENT, RestorationStage.MOVEMENT: RestorationStage.RISING}


class AdvanceRestoration(Command):
    record_id: int


@player_action("restoration:advance", ActionKind.EDIT_RECORD)
async def restoration_advance(scope: PlayerScope, command: AdvanceRestoration) -> Effect:
    row = await scope.session.get(RestorationRow, command.record_id)
    if row is None:
        raise NotFoundError("There is no such restoration.")
    if row.stage not in OPEN_STAGES:
        raise ValidationFailedError(f"The restoration has already {spoken(row.stage)}.")
    ctx = await scope.context("restoration_advance")
    if row.stage in NEXT_STAGE:
        row.stage = NEXT_STAGE[row.stage]
        return Effect(f"The restoration moves on to its {spoken(row.stage)}.", target_node_id=row.fallen_polity_id)
    realm = await restore(ctx, row, RestorationTally())
    if realm is None:
        return Effect("None of its old lands could be taken back, and the restoration failed.", target_node_id=row.fallen_polity_id)
    return Effect(f"{realm.name} stands again.", target_node_id=realm.id)
