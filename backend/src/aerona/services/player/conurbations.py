from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.city_rules import ConurbationRow
from aerona.domain.enums.action import ActionKind
from aerona.engine.city_rules.book import CityTally
from aerona.engine.city_rules.conurbations import split
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class SplitConurbation(Command):
    record_id: int


@player_action("conurbation:split", ActionKind.EDIT_RECORD)
async def conurbation_split(scope: PlayerScope, command: SplitConurbation) -> Effect:
    row = await scope.session.get(ConurbationRow, command.record_id)
    if row is None:
        raise NotFoundError("There is no such city.")
    if row.split_epoch is not None:
        raise ValidationFailedError("That city has already split apart.")
    ctx = await scope.context("conurbation_split")
    await split(ctx, row, CityTally())
    return Effect("The city splits apart into its settlements again.", target_node_id=row.core_entity_id)
