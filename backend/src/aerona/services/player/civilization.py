from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.civilization import (
    enforce_debt,
    forgive_debt,
    grant_independence,
    impose_loan,
    order_adoption,
    order_barter,
    order_previous_creation,
    order_treaty,
    reclaim_colony,
    set_tier,
)
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Tier(Command):
    entity_id: int
    tier: int
    lock: bool = False


class Independence(Command):
    colony_id: int
    war: bool = False


class Reclaim(Command):
    mother_id: int
    colony_id: int


class WorldTarget(Command):
    world_id: int


class Loan(Command):
    lender_id: int
    borrower_id: int
    amount: int


class DebtTarget(Command):
    bond_id: int


class Pair(Command):
    first_id: int
    second_id: int


class Adoption(Command):
    adopter_id: int
    child_id: int


class Treaty(Command):
    first_id: int
    second_id: int
    alliance: bool = False


@player_action("civilization:tier", ActionKind.SET_TIER)
async def tier(scope: PlayerScope, command: Tier) -> Effect:
    entity = await set_tier(scope.session, scope.rules, command.entity_id, command.tier, lock=command.lock)
    state = "and held there" if command.lock else "and left to change"
    return Effect(f"{entity.name} stands at civilization tier {command.tier} {state}.", entity.id, values={"tier": command.tier})


@player_action("civilization:independence", ActionKind.GRANT_INDEPENDENCE)
async def independence(scope: PlayerScope, command: Independence) -> Effect:
    return Effect(await grant_independence(scope.session, scope.rules, command.colony_id, war=command.war), command.colony_id)


@player_action("civilization:reclaim", ActionKind.RECLAIM_COLONY)
async def reclaim(scope: PlayerScope, command: Reclaim) -> Effect:
    await reclaim_colony(scope.session, scope.rules, command.mother_id, command.colony_id)
    return Effect("The colony is ruled by its mother again.", command.colony_id)


@player_action("world:previous_creation", ActionKind.REVEAL_PREVIOUS_CREATION)
async def previous_creation(scope: PlayerScope, command: WorldTarget) -> Effect:
    ruin = await order_previous_creation(scope.session, scope.rules, command.world_id)
    return Effect(f"The ruins of an older creation surfaced: {ruin.name}.", ruin.id, created_ids=(ruin.id,))


@player_action("civilization:loan", ActionKind.LEND)
async def loan(scope: PlayerScope, command: Loan) -> Effect:
    return Effect(await impose_loan(scope.session, scope.rules, command.lender_id, command.borrower_id, command.amount), command.borrower_id)


@player_action("civilization:forgive_debt", ActionKind.FORGIVE_DEBT)
async def forgive(scope: PlayerScope, command: DebtTarget) -> Effect:
    await forgive_debt(scope.session, scope.rules, command.bond_id)
    return Effect("The debt was forgiven.")


@player_action("civilization:enforce_debt", ActionKind.REPAY)
async def enforce(scope: PlayerScope, command: DebtTarget) -> Effect:
    return Effect(await enforce_debt(scope.session, scope.rules, command.bond_id))


@player_action("civilization:barter", ActionKind.BARTER)
async def barter(scope: PlayerScope, command: Pair) -> Effect:
    return Effect(await order_barter(scope.session, scope.rules, command.first_id, command.second_id), command.second_id)


@player_action("civilization:adoption", ActionKind.ADOPT)
async def adoption(scope: PlayerScope, command: Adoption) -> Effect:
    return Effect(await order_adoption(scope.session, scope.rules, command.adopter_id, command.child_id), command.child_id)


@player_action("civilization:treaty", ActionKind.INTERWORLD_TREATY)
async def treaty(scope: PlayerScope, command: Treaty) -> Effect:
    return Effect(await order_treaty(scope.session, scope.rules, command.first_id, command.second_id, alliance=command.alliance), command.second_id)
