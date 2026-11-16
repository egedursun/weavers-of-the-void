from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.market import run_market, write_off_debt
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class DebtTarget(Command):
    bond_id: int


class Empty(Command):
    pass


@player_action("market:write_off", ActionKind.FORGIVE_DEBT)
async def write_off(scope: PlayerScope, command: DebtTarget) -> Effect:
    return Effect(await write_off_debt(scope.session, scope.rules, command.bond_id))


@player_action("market:run", ActionKind.OTHER)
async def run_now(scope: PlayerScope, command: Empty) -> Effect:
    await run_market(scope.session, scope.rules)
    return Effect("The markets of the world opened: goods moved, debts came due and deposits ran down.")
