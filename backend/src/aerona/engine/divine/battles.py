from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.son import PowerEffect
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, alive, god_of
from aerona.engine.divine.politics import god_grudge
from aerona.engine.divine.standing import standing_row
from aerona.engine.divine.wounds import name_exposure
from aerona.engine.faith.book import patron_node
from aerona.engine.military.battle import Side
from aerona.engine.mythic.offices import conquer_offices
from aerona.engine.mythic.servitors import host_of, shake_host
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.strength import has_power


@dataclass
class Hand:
    side: Side
    god: God
    smites: bool
    might: float


def style_of(god: God) -> bool:
    return not isinstance(god, SonRow) or god.wrath >= god.mercy


async def might_of(ctx: TickContext, god: God) -> float:
    table = ctx.rules.divine_wounds
    base = (god.strength + god.will) / 2 + god.level if isinstance(god, SonRow) else float(god.power)
    return (base + await host_of(ctx.session, ctx.rules, god.id)) * await name_exposure(ctx.session, god.id, table.name_exposure_pct)


async def pay(ctx: TickContext, god: God) -> bool:
    table = ctx.rules.domains
    if isinstance(god, SonRow):
        if god.essence < table.battle_essence:
            return False
        god.essence -= table.battle_essence
        return True
    if god.power < table.battle_foreign_power:
        return False
    god.power -= table.battle_foreign_power
    return True


async def willing(ctx: TickContext, god: God, stream: str) -> bool:
    table = ctx.rules.domains
    chance = table.battle_intervene_chance
    if isinstance(god, SonRow) and await has_power(ctx.session, god.id, PowerEffect.WAR_FATHER):
        chance = min(PERCENT, chance * table.battle_war_father_mult)
    return ctx.rng(stream).chance(chance)


async def hand_of(ctx: TickContext, side: Side, god: God | None, stream: str) -> Hand | None:
    if god is None or not alive(god) or held(god.id) or not await willing(ctx, god, f"{stream}.{god.id}"):
        return None
    if isinstance(god, ForeignGodRow) and god.power <= 0:
        return None
    if not await pay(ctx, god):
        return None
    return Hand(side, god, style_of(god), await might_of(ctx, god))


def lay(ctx: TickContext, hand: Hand) -> None:
    table = ctx.rules.domains
    if hand.smites:
        hand.side.divine_strike_pct = table.battle_strike_pct
    else:
        hand.side.divine_shield = table.battle_shield_morale
        hand.side.morale_parts["god_shield"] = table.battle_shield_morale


async def contest(ctx: TickContext, first: Hand, second: Hand, stream: str) -> tuple[Hand, Hand]:
    spread = ctx.rules.domains.battle_contest_spread_pct / PERCENT
    rng = ctx.rng(f"{stream}.contest")
    roll_a = first.might * rng.uniform(1 - spread, 1 + spread)
    roll_b = second.might * rng.uniform(1 - spread, 1 + spread)
    return (first, second) if (roll_a, -first.god.id) >= (roll_b, -second.god.id) else (second, first)


async def awe(ctx: TickContext, hand: Hand) -> None:
    if held(hand.side.entity.id, hand.god.id):
        return
    row = await standing_row(ctx, hand.side.entity.id, hand.god.id)
    if "awe" not in row.locked:
        row.awe = clamp_int(row.awe + ctx.rules.divine_standing.act_awe, 0, PERCENT)
    row.epoch = ctx.epoch


async def intervene(ctx: TickContext, war_id: int, sequence: int, first: Side, second: Side) -> int:
    stream = f"battle_god.{war_id}.{sequence}"
    patrons = [await god_of(ctx.session, await patron_node(ctx.session, side.entity.id)) for side in (first, second)]
    if patrons[0] is not None and patrons[1] is not None and patrons[0].id == patrons[1].id:
        return 0
    found = [await hand_of(ctx, side, god, f"{stream}.{side.entity.id}") for side, god in zip((first, second), patrons, strict=True)]
    hands = [hand for hand in found if hand is not None]
    if not hands:
        return 0
    son = next((hand.god.id for hand in hands if isinstance(hand.god, SonRow)), None)
    if len(hands) == 2:
        winner, loser = await contest(ctx, hands[0], hands[1], stream)
        lay(ctx, winner)
        loser.side.divine_spurned = ctx.rules.domains.battle_spurned_morale
        await awe(ctx, winner)
        await god_grudge(ctx, loser.god.id, winner.god.id, MemoryKind.HUMILIATED_ME, f"overcame it in the battle for {loser.side.entity.name}")
        await conquer_offices(ctx, winner.god.id, loser.god.id, stream)
        await shake_host(ctx, loser.god.id)
        await note(
            ctx,
            f"{winner.god.name} overcame {loser.god.name} in the battle between {first.entity.name} and {second.entity.name}; "
            f"the intervention of {loser.god.name} turned against {loser.side.entity.name}.",
            key="divine.battle_contest",
            ids=[first.entity.id, second.entity.id],
            son_id=son,
            kind=ChronicleKind.CHALLENGE,
            world_id=first.entity.world_id,
        )
        return 2
    for hand in hands:
        lay(ctx, hand)
        await awe(ctx, hand)
        await note(
            ctx,
            f"{hand.god.name} intervened in the battle for {hand.side.entity.name}" + (", striking its foes." if hand.smites else ", steadying its faithful."),
            key="divine.battle_hand",
            ids=[hand.side.entity.id],
            son_id=hand.god.id if isinstance(hand.god, SonRow) else None,
            kind=ChronicleKind.CHALLENGE,
            world_id=hand.side.entity.world_id,
        )
    return len(hands)
