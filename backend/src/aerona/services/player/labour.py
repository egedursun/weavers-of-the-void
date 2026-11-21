from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.labour import LabourDisputeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.labour import DisputeOutcome
from aerona.engine.labour.bodies import LabourTally
from aerona.engine.labour.disputes import end_dispute
from aerona.engine.labour.spread import spread_from
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

ENDINGS = frozenset({DisputeOutcome.WON, DisputeOutcome.LOST, DisputeOutcome.SETTLED})


class EndDispute(Command):
    record_id: int
    outcome: DisputeOutcome = DisputeOutcome.SETTLED


@player_action("labour_dispute:end", ActionKind.EDIT_RECORD)
async def labour_dispute_end(scope: PlayerScope, command: EndDispute) -> Effect:
    dispute = await scope.session.get(LabourDisputeRow, command.record_id)
    if dispute is None:
        raise NotFoundError("There is no such dispute.")
    if dispute.outcome is not DisputeOutcome.ONGOING:
        raise ValidationFailedError(f"The dispute has already ended, {spoken(dispute.outcome)}.")
    if command.outcome not in ENDINGS:
        raise ValidationFailedError("A dispute ends won, lost or settled.")
    ctx = await scope.context("labour_dispute_end")
    tally = LabourTally()
    await end_dispute(ctx, dispute, command.outcome, tally)
    await spread_from(ctx, dispute, tally)
    return Effect(f"{dispute.name.capitalize()} ended {spoken(command.outcome)}.", target_node_id=dispute.body_node_id)
