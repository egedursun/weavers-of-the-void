from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.creator import CreatorSignKind
from aerona.engine.transition import pour_essence
from aerona.services import faith
from aerona.services.gods import creator_mood, death, goals, reputation
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Pour(Command):
    amount: int


class Sign(Command):
    kind: CreatorSignKind
    target_id: int | None = None


class Protection(Command):
    entity_id: int
    protected: bool = True


class ForeignStrike(Command):
    god_id: int
    entity_id: int


class SonTarget(Command):
    son_id: int


class Empty(Command):
    pass


class FirstFaith(Command):
    entity_id: int
    source_id: int | None = None


@player_action("essence:pour", ActionKind.POUR_ESSENCE)
async def pour(scope: PlayerScope, command: Pour) -> Effect:
    result = await pour_essence(await scope.context("pour_essence"), command.amount)
    return Effect(
        f"{several(result.given, 'measure', 'measures')} of fertility rose in the barren lands.", essence_spent=command.amount, values={"given": result.given}
    )


@player_action("creator:sign", ActionKind.CREATOR_SIGN)
async def sign(scope: PlayerScope, command: Sign) -> Effect:
    reached = await creator_mood.trigger_sign(scope.session, scope.rules, command.kind, command.target_id, scope.publish)
    if reached is None:
        return Effect("The Creator fell silent.")
    return Effect(f"A sign of {command.kind.value} reached {reached.name}.", reached.id)


@player_action("mortal:protect", ActionKind.EDIT_RECORD)
async def protect(scope: PlayerScope, command: Protection) -> Effect:
    changed = await death.grant_protection(scope.session, scope.rules, command.entity_id, command.protected)
    state = "shielded from death" if command.protected else "no longer shielded from death"
    return Effect(f"The mortal is {state}." if changed else f"The mortal was already {state}.", command.entity_id, values={"changed": changed})


@player_action("foreign_god:strike", ActionKind.TAKE_LIFE)
async def foreign_strike(scope: PlayerScope, command: ForeignStrike) -> Effect:
    outcome = await death.order_foreign_strike(scope.session, scope.rules, command.god_id, command.entity_id)
    return Effect(outcome.text, command.entity_id, values={"success": outcome.success, "percent": outcome.percent})


@player_action("reputation:drift", ActionKind.PUSH_REPUTATION)
async def drift(scope: PlayerScope, command: SonTarget) -> Effect:
    view = await reputation.apply_drift_now(scope.session, scope.rules, command.son_id)
    values: dict[str, int | float | str | bool | None] = {"love": view.love, "fear": view.fear, "forgotten": view.forgotten, "label": view.label.value}
    return Effect(f"The son's view of the Creator settled: {view.label.value.replace('_', ' ')}.", command.son_id, values=values)


@player_action("goals:evaluate", ActionKind.EVALUATE_GOALS)
async def evaluate(scope: PlayerScope, command: Empty) -> Effect:
    result = await goals.evaluate_now(scope.session, scope.rules)
    values: dict[str, int | float | str | bool | None] = {
        "completed": len(result.completed),
        "failed": len(result.failed),
        "earned": len(result.earned),
    }
    return Effect(
        f"Goals weighed: {len(result.completed)} completed, {len(result.failed)} failed, {several(len(result.earned), 'achievement', 'achievements')} earned.",
        values=values,
    )


@player_action("faith:first", ActionKind.WORSHIP)
async def first_faith(scope: PlayerScope, command: FirstFaith) -> Effect:
    patron = await faith.give_first_faith(scope.session, scope.rules, command.entity_id, command.source_id)
    return Effect("The community found its first faith.", command.entity_id, values={"patron_node_id": patron.patron_node_id})
