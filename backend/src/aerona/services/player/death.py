from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.gods.devotion import SchemeKind
from aerona.services.gods import death
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class ResurrectSon(Command):
    son_id: int


class TakeLife(Command):
    entity_id: int
    how: str = ""


class SiblingScheme(Command):
    sibling_id: int
    son_id: int
    kind: SchemeKind


class ScatterBones(Command):
    sibling_id: int
    son_id: int


class KillSon(Command):
    son_id: int
    reason: str = ""


@player_action("resurrect:son", ActionKind.RESURRECT_SON)
async def resurrect_son(scope: PlayerScope, command: ResurrectSon) -> Effect:
    son = await death.resurrect(scope.session, scope.rules, command.son_id, scope.publish)
    return Effect(f"{son.name} rose again by the Creator's hand.", son.id)


@player_action("take_life", ActionKind.TAKE_LIFE)
async def take_life(scope: PlayerScope, command: TakeLife) -> Effect:
    mortal = await guards.entity(scope.session, command.entity_id)
    if mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living, named mortal's life can be taken.")
    outcome = await death.take_life(
        scope.session, scope.rules, mortal.id, guards.clip(command.how, scope.rules.god_actions.inspiration_max_chars), scope.publish
    )
    return Effect(outcome.text, mortal.id)


@player_action("kill:son", ActionKind.KILL_SON)
async def kill_son(scope: PlayerScope, command: KillSon) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    name = son.name
    await death.kill_son(scope.session, scope.rules, son.id, guards.clip(command.reason, scope.rules.god_actions.inspiration_max_chars), scope.publish)
    return Effect(f"{name} died by the Creator's hand.", son.id, essence_spent=scope.rules.death.creator_kill_son_cost)


@player_action("sibling:scheme", ActionKind.SIBLING_SCHEME)
async def sibling_scheme(scope: PlayerScope, command: SiblingScheme) -> Effect:
    sibling = await guards.son(scope.session, command.sibling_id)
    son = await guards.son(scope.session, command.son_id)
    result = await death.order_scheme(scope.session, scope.rules, sibling.id, son.id, command.kind)
    return Effect(
        result.text,
        son.id,
        values={"contribution": result.contribution, "devotion": result.devotion, "slept": result.slept},
        tool=f"sibling:{command.kind.value}",
    )


@player_action("sibling:scatter", ActionKind.SCATTER_BONES)
async def scatter_bones(scope: PlayerScope, command: ScatterBones) -> Effect:
    sibling = await guards.son(scope.session, command.sibling_id)
    son = await guards.son(scope.session, command.son_id)
    result = await death.order_scatter(scope.session, scope.rules, sibling.id, son.id)
    return Effect(result.text, son.id, values={"contribution": result.contribution, "devotion": result.devotion})
