from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.referendums import ReferendumResult
from aerona.engine.referendums.book import ReferendumTally
from aerona.engine.referendums.voting import answer
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

DECIDED = frozenset({ReferendumResult.PASSED, ReferendumResult.FAILED, ReferendumResult.VOID})


class DecideReferendum(Command):
    record_id: int
    result: ReferendumResult = ReferendumResult.PASSED


@player_action("referendum:decide", ActionKind.EDIT_RECORD)
async def referendum_decide(scope: PlayerScope, command: DecideReferendum) -> Effect:
    row = await scope.session.get(ReferendumRow, command.record_id)
    if row is None:
        raise NotFoundError("There is no such vote.")
    if row.result is not ReferendumResult.PENDING:
        raise ValidationFailedError(f"The vote is already {spoken(row.result)}.")
    if command.result not in DECIDED:
        raise ValidationFailedError("A vote is decided passed, failed or void.")
    ctx = await scope.context("referendum_decide")
    holder = await scope.session.get(EntityRow, row.holder_node_id)
    row.result, row.held_epoch = command.result, ctx.epoch
    if holder is not None and command.result is not ReferendumResult.VOID:
        await answer(ctx, row, holder, ReferendumTally())
    return Effect(f"{row.name.capitalize()} is {spoken(command.result)}.", target_node_id=row.holder_node_id)
