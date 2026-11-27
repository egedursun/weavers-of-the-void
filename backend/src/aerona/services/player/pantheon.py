from enum import StrEnum

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.divine import BargainGain, BargainPrice
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.son import Stat
from aerona.engine.cosmos.actions import BargainTerms, bargain_with_outer
from aerona.engine.gods.essence_flow import send_essence
from aerona.engine.phases.pantheon import order_god_war, order_temple_raid, provoke_duel, wake_foreign_god
from aerona.engine.phases.sons import set_son_relation
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class SonDuel(Command):
    challenger_id: int
    defender_id: int
    stat: Stat = Stat.STRENGTH


class GodWar(Command):
    son_id: int
    god_id: int


class TempleRaid(Command):
    god_id: int
    temple_id: int


class ForeignGodTarget(Command):
    god_id: int


class OuterBargainMode(StrEnum):
    FORCE = "force"
    FORBID = "forbid"
    ALLOW = "allow"


class OuterBargainOrder(Command):
    son_id: int
    mode: OuterBargainMode
    outer_id: int | None = None
    request: str = "the Creator's command"
    gain: BargainGain = BargainGain.ESSENCE
    price: BargainPrice = BargainPrice.WORLD_SANITY
    price_domain: Domain | None = None
    price_world_id: int | None = None


class SonEssence(Command):
    son_id: int
    to_son_id: int | None = None
    amount: int


class SonRelation(Command):
    first_id: int
    second_id: int
    value: int


@player_action("son:duel", ActionKind.CHALLENGE)
async def duel(scope: PlayerScope, command: SonDuel) -> Effect:
    return Effect(await provoke_duel(scope.session, scope.rules, command.challenger_id, command.defender_id, command.stat), command.challenger_id)


@player_action("son:god_war", ActionKind.FOREIGN_GOD_WAR)
async def god_war(scope: PlayerScope, command: GodWar) -> Effect:
    await guards.living_son(scope.session, command.son_id)
    await guards.foreign_god(scope.session, command.god_id)
    return Effect(await order_god_war(scope.session, scope.rules, command.son_id, command.god_id), command.son_id)


@player_action("foreign_god:raid_temple", ActionKind.DESTROY)
async def raid_temple(scope: PlayerScope, command: TempleRaid) -> Effect:
    return Effect(await order_temple_raid(scope.session, scope.rules, command.god_id, command.temple_id), command.temple_id)


@player_action("foreign_god:wake", ActionKind.WAKE_FOREIGN_GOD)
async def wake(scope: PlayerScope, command: ForeignGodTarget) -> Effect:
    god = await wake_foreign_god(scope.session, scope.rules, command.god_id)
    return Effect(f"{god.name} woke.", god.id)


@player_action("son:relation", ActionKind.SET_SON_RELATION)
async def relation(scope: PlayerScope, command: SonRelation) -> Effect:
    if not RELATION_MIN <= command.value <= RELATION_MAX:
        raise ValidationFailedError(f"A relation lies between {RELATION_MIN} and {RELATION_MAX}.")
    first = await guards.son(scope.session, command.first_id)
    second = await guards.son(scope.session, command.second_id)
    value = await set_son_relation(await scope.context("son_relation"), first.id, second.id, command.value)
    return Effect(f"{first.name} and {second.name} now stand at {value}.", first.id, values={"relation": value})


@player_action("son:outer_bargain", ActionKind.OUTER_BARGAIN)
async def outer_bargain(scope: PlayerScope, command: OuterBargainOrder) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    if command.mode is OuterBargainMode.FORBID:
        son.outer_bargain_forbidden = True
        return Effect(f"{son.name} may no longer bargain with what lies outside.", son.id)
    if command.mode is OuterBargainMode.ALLOW:
        son.outer_bargain_forbidden = False
        return Effect(f"{son.name} may bargain with what lies outside again.", son.id)
    if command.outer_id is None:
        raise ValidationFailedError("Name the outer being the son must bargain with.")
    terms = BargainTerms(command.gain, command.price, command.price_domain, command.price_world_id)
    gain = await bargain_with_outer(await scope.context("outer_bargain"), son.id, command.outer_id, command.request, terms)
    return Effect(f"{son.name} bargained with the outer being by command.", son.id, values={"gain": gain})


@player_action("son:send_essence", ActionKind.GIFT)
async def send_essence_lever(scope: PlayerScope, command: SonEssence) -> Effect:
    giver = await guards.living_son(scope.session, command.son_id)
    receiver: SonRow | CreatorRow = await guards.living_son(scope.session, command.to_son_id) if command.to_son_id is not None else await scope.creator()
    sent = await send_essence(await scope.context("send_essence"), giver, receiver, command.amount)
    return Effect(f"{giver.name} sent {sent} essence to {receiver.name}.", giver.id, values={"sent": sent})
