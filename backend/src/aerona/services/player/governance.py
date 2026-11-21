from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.governance import OrgMergerRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.governance import OPEN_MERGER_STAGES
from aerona.engine.governance.mergers import advance_merger
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class OrgMergerTarget(Command):
    record_id: int


@player_action("org_merger:advance", ActionKind.EDIT_RECORD)
async def org_merger_advance(scope: PlayerScope, command: OrgMergerTarget) -> Effect:
    merger = await scope.session.get(OrgMergerRow, command.record_id)
    if merger is None:
        raise NotFoundError("There is no such bid.")
    if merger.stage not in OPEN_MERGER_STAGES:
        raise ValidationFailedError(f"The bid has already ended, {spoken(merger.stage)}.")
    outcome = await advance_merger(await scope.context("org_merger_advance"), merger)
    if outcome is None:
        raise ValidationFailedError("The bid cannot move: a party or the bid itself is held, or a party is gone.")
    return Effect(f"The bid of {merger.price} now stands {spoken(merger.stage)}.", target_node_id=merger.target_node_id)
