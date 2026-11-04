from dataclasses import dataclass, field

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.mind import TraitEffect, ValueAxis
from aerona.engine.body.book import effective
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import mounted_power
from aerona.engine.economy.sanctity import holy_strike
from aerona.engine.lore.arms import best_weapon, grip, guard_of, held_profiles
from aerona.engine.mind.book import effect_of, scaled_by, values_for
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import equipment, weapon_power
from aerona.rules.registry import Rules

ARMOUR_CAP = 0.8
REACH_ITEMS = 2


@dataclass
class Fighter:
    entity: EntityRow
    power: float
    hp: int
    armour: int
    reach: int
    honour: int
    mercy: int
    stamina: int = PERCENT
    harm: int = 0
    disarmed: bool = False


@dataclass
class Bout:
    winner: Fighter
    loser: Fighter
    end: DuelEnd
    context: DuelContext
    exchanges: int
    killed: bool = False
    spared: bool = False
    log: list[str] = field(default_factory=list)


async def fighter(ctx: TickContext, hero: EntityRow, foe: EntityRow | None = None) -> Fighter:
    campaigns = ctx.rules.campaigns
    nerve = scaled_by(await effect_of(ctx.session, hero.id, TraitEffect.COURAGE, ctx.rules.traits.effect_scale_pct))
    base = (
        await effective(ctx.session, hero, "strength", rules=ctx.rules)
        + await effective(ctx.session, hero, "agility", rules=ctx.rules) / campaigns.duel_agility_divisor
        + await weapon_power(ctx.session, ctx.rules, hero.id, campaigns.duel_weapon_mult)
    ) * nerve
    items = await equipment(ctx.session, hero.id)
    values = await values_for(ctx.session, hero.id)
    held = await held_profiles(ctx.session, hero.id)
    blade = best_weapon(held)
    reach = blade.reach if blade is not None else min(REACH_ITEMS, sum(1 for item in items if (stat(item, "damage") or 0) > 0))
    return Fighter(
        entity=hero,
        power=base * (grip(blade) if blade is not None else 1.0) * await mounted_power(ctx, hero.id) * await holy_strike(ctx.session, ctx.rules, hero.id, foe),
        hp=stat(hero, "hp") or campaigns.hero_default_hp,
        armour=sum(stat(item, "protection") or 0 for item in items) + guard_of(held),
        reach=reach,
        honour=values.get(ValueAxis.HONOUR, 0),
        mercy=values.get(ValueAxis.MERCY, 0),
    )


def swing(rules: Rules, rng: SeededRandom, fighter: Fighter, foe: Fighter, first: bool) -> float:
    campaigns, table = rules.campaigns, rules.duels
    reach = 1 + table.reach_pct / PERCENT if first and fighter.reach > foe.reach else 1.0
    armed = 0.3 if fighter.disarmed else 1.0
    return fighter.power * (0.5 + fighter.stamina / (2 * PERCENT)) * reach * armed + rng.die(campaigns.duel_die) * campaigns.duel_die_mult


def wound(rules: Rules, target: Fighter, margin: float, total: float) -> int:
    table = rules.duels
    shield = min(ARMOUR_CAP, target.armour / PERCENT * table.armour_pct / PERCENT)
    harm = round_half_up(table.hit_hp * (0.5 + margin / max(1.0, total)) * (1 - shield))
    target.harm += harm
    return harm


def downed(rules: Rules, rng: SeededRandom, winner: Fighter, loser: Fighter, context: DuelContext) -> tuple[DuelEnd, bool, bool]:
    if winner.mercy >= rules.duels.mercy_spare and context is not DuelContext.TRIAL:
        return DuelEnd.CRIPPLED, False, True
    if rng.chance(rules.campaigns.duel_death_chance) or context is DuelContext.TRIAL:
        return DuelEnd.DEATH, True, False
    return DuelEnd.CRIPPLED, False, False


def bout(rules: Rules, rng: SeededRandom, first: Fighter, second: Fighter, context: DuelContext) -> Bout:
    table = rules.duels
    count = table.exchanges_min + rng.below(max(1, table.exchanges_max - table.exchanges_min + 1))
    log: list[str] = []
    for index in range(count):
        roll_a, roll_b = swing(rules, rng, first, second, index == 0), swing(rules, rng, second, first, index == 0)
        hitter, target = (first, second) if roll_a >= roll_b else (second, first)
        margin, total = abs(roll_a - roll_b), max(roll_a, roll_b)
        if not target.disarmed and rng.chance(table.disarm_chance) and margin < total / 4:
            target.disarmed = True
            log.append(f"{hitter.entity.name} struck the weapon from {target.entity.name}'s hand")
        else:
            log.append(f"{hitter.entity.name} hit {target.entity.name} for {wound(rules, target, margin, total)}")
        for one in (first, second):
            one.stamina = max(0, one.stamina - table.stamina_loss)
        if target.harm >= target.hp:
            end, killed, spared = downed(rules, rng, hitter, target, context)
            return Bout(hitter, target, end, context, index + 1, killed, spared, log)
        if target.harm * 2 >= target.hp and target.honour < table.yield_honour and context is not DuelContext.TRIAL:
            return Bout(hitter, target, DuelEnd.YIELD, context, index + 1, log=log)
        if target.disarmed and target.honour < table.yield_honour:
            return Bout(hitter, target, DuelEnd.DISARM, context, index + 1, log=log)
    winner, loser = (first, second) if first.harm <= second.harm else (second, first)
    return Bout(winner, loser, DuelEnd.EXHAUSTION, context, count, log=log)
