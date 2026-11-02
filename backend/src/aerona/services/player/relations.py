from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.engine.services.community_relations import has_blood_feud, set_relation, start_blood_feud
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SET_REASON = "the god's decree"
FEUD_REASON = "the god declared a blood feud"
COMMUNITY_ONLY = "Relations hold between communities only."


class SetRelation(Command):
    first_id: int
    second_id: int
    value: int


class DeclareFeud(Command):
    first_id: int
    second_id: int


async def pair(scope: PlayerScope, first_id: int, second_id: int) -> tuple[int, int, str, str]:
    if first_id == second_id:
        raise ValidationFailedError("A community holds no relation with itself.")
    first = await guards.canon_entity(scope.session, first_id)
    second = await guards.canon_entity(scope.session, second_id)
    guards.of_types(first, COMMUNITY_TYPES, COMMUNITY_ONLY)
    guards.of_types(second, COMMUNITY_TYPES, COMMUNITY_ONLY)
    return first.id, second.id, first.name, second.name


@player_action("relation:set", ActionKind.DIPLOMACY)
async def set_community_relation(scope: PlayerScope, command: SetRelation) -> Effect:
    if not RELATION_MIN <= command.value <= RELATION_MAX:
        raise ValidationFailedError(f"A relation must lie between {RELATION_MIN} and {RELATION_MAX}.")
    first_id, second_id, first_name, second_name = await pair(scope, command.first_id, command.second_id)
    value = await set_relation(await scope.context("relation"), first_id, second_id, command.value, SET_REASON)
    return Effect(f"The relation between {first_name} and {second_name} was set to {value}.", first_id, values={"value": value})


@player_action("feud:start", ActionKind.DIPLOMACY)
async def declare_feud(scope: PlayerScope, command: DeclareFeud) -> Effect:
    first_id, second_id, first_name, second_name = await pair(scope, command.first_id, command.second_id)
    if await has_blood_feud(scope.session, first_id, second_id):
        raise ValidationFailedError(f"{first_name} and {second_name} already hold a blood feud.")
    value = await start_blood_feud(await scope.context("feud"), first_id, second_id, FEUD_REASON)
    return Effect(f"A blood feud was declared between {first_name} and {second_name}.", first_id, values={"value": value})
