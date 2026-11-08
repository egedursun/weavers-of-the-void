from dataclasses import dataclass, field

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.mind import TraitEffect, ValueAxis
from aerona.engine.body.book import effective
from aerona.engine.body.strike import worn_layers
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import mounted_power
from aerona.engine.economy.sanctity import holy_strike
from aerona.engine.lore.arms import best_weapon, burden_of, grip, guard_of, held_profiles, war_magic, ward_magic
from aerona.engine.mind.book import effect_of, scaled_by, values_for
from aerona.engine.mind.inspiration import resolute
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.primitives.strength import equipment, weapon_power
from aerona.engine.relations.passions import invoke
from aerona.rules.registry import Rules

ARMOUR_CAP = 0.8
SLIPPERY = frozenset({TerrainKind.MARSH, TerrainKind.ICE_SHEET, TerrainKind.TUNDRA, TerrainKind.RIVER_VALLEY, TerrainKind.FLESH})
WET = frozenset({WeatherKind.RAIN, WeatherKind.DOWNPOUR, WeatherKind.STORM, WeatherKind.SNOW, WeatherKind.BLIZZARD, WeatherKind.HAIL})
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
    burden: int = 0
    stamina: int = PERCENT
    harm: int = 0
    disarmed: bool = False
    footing: int = PERCENT
    pain: int = 0


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
    hits: list[tuple[int, int]] = field(default_factory=list)


async def heroic_effort(ctx: TickContext, hero: EntityRow) -> float:
    table = ctx.rules.aspirations
    lift = 1 + table.resolve_pct / PERCENT if await resolute(ctx.session, hero.id) else 1.0
    profile = await ctx.session.get(MortalProfileRow, hero.id)
    if profile is not None and profile.conviction >= table.conviction_spend and table.conviction_spend and not is_held(profile, "conviction"):
        profile.conviction -= table.conviction_spend
        lift *= 1 + table.conviction_spend_pct / PERCENT
    return lift


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
    broken = ctx.rules.item_wear.broken
    blade = best_weapon(held, broken)
    reach = blade.reach if blade is not None else min(REACH_ITEMS, sum(1 for item in items if (stat(item, "damage") or 0) > 0))
    magic = await war_magic(ctx.session, ctx.rules, blade)
    holy = await holy_strike(ctx.session, ctx.rules, hero.id, foe)
    holy *= await heroic_effort(ctx, hero)
    holy *= await invoke(ctx, hero, [foe.id] if foe is not None else None)
    return Fighter(
        entity=hero,
        power=base * (grip(blade) if blade is not None else 1.0) * magic * await mounted_power(ctx, hero.id) * holy,
        hp=stat_or(hero, "hp", campaigns.hero_default_hp),
        armour=sum(stat(item, "protection") or 0 for item in items) + guard_of(held, broken) + await ward_magic(ctx.session, ctx.rules, held),
        reach=reach,
        honour=values.get(ValueAxis.HONOUR, 0),
        mercy=values.get(ValueAxis.MERCY, 0),
        burden=burden_of(held, broken) * ctx.rules.item_powers.weight_fatigue_pct // PERCENT + await armour_burden(ctx, hero.id),
        stamina=PERCENT - await spent_strength(ctx, hero.id),
    )


async def armour_burden(ctx: TickContext, hero_id: int) -> int:
    layers = await worn_layers(ctx.session, hero_id)
    density = sum(layer.props.density for layer in layers) / len(layers) if layers else 0
    return round(density * ctx.rules.tissues.duel_density_burden / PERCENT)


async def spent_strength(ctx: TickContext, hero_id: int) -> int:
    body = await ctx.session.get(BodyRow, hero_id)
    return body.exertion if body is not None else 0


def swing(rules: Rules, rng: SeededRandom, fighter: Fighter, foe: Fighter, first: bool) -> float:
    campaigns, table = rules.campaigns, rules.duels
    reach = 1 + table.reach_pct / PERCENT if first and fighter.reach > foe.reach else 1.0
    armed = 0.3 if fighter.disarmed else 1.0
    footing = fighter.footing / PERCENT
    pain = max(0.2, 1 - fighter.pain / (2 * PERCENT))
    return fighter.power * (0.5 + fighter.stamina / (2 * PERCENT)) * reach * armed * footing * pain + rng.die(campaigns.duel_die) * campaigns.duel_die_mult


def wound(rules: Rules, target: Fighter, margin: float, total: float) -> int:
    table = rules.duels
    shield = min(ARMOUR_CAP, target.armour / PERCENT * table.armour_pct / PERCENT)
    harm = round_half_up(table.hit_hp * (0.5 + margin / max(1.0, total)) * (1 - shield))
    target.harm += harm
    target.pain = min(PERCENT, target.pain + round_half_up(harm * table.pain_pct / PERCENT))
    if harm >= table.hit_hp:
        target.footing = max(table.footing_floor, target.footing - table.stagger)
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
    hits: list[tuple[int, int]] = []
    for index in range(count):
        roll_a, roll_b = swing(rules, rng, first, second, index == 0), swing(rules, rng, second, first, index == 0)
        hitter, target = (first, second) if roll_a >= roll_b else (second, first)
        margin, total = abs(roll_a - roll_b), max(roll_a, roll_b)
        if not target.disarmed and rng.chance(table.disarm_chance) and margin < total / 4:
            target.disarmed = True
            log.append(f"{hitter.entity.name} struck the weapon from {target.entity.name}'s hand")
        else:
            harm = wound(rules, target, margin, total)
            hits.append((target.entity.id, harm))
            log.append(f"{hitter.entity.name} hit {target.entity.name} for {harm}")
        for one in (first, second):
            one.stamina = max(0, one.stamina - table.stamina_loss - one.burden)
        if target.harm >= target.hp:
            end, killed, spared = downed(rules, rng, hitter, target, context)
            return Bout(hitter, target, end, context, index + 1, killed, spared, log, hits)
        if target.harm * 2 >= target.hp and target.honour < table.yield_honour and context is not DuelContext.TRIAL:
            return Bout(hitter, target, DuelEnd.YIELD, context, index + 1, log=log, hits=hits)
        if target.disarmed and target.honour < table.yield_honour:
            return Bout(hitter, target, DuelEnd.DISARM, context, index + 1, log=log, hits=hits)
    winner, loser = (first, second) if first.harm <= second.harm else (second, first)
    return Bout(winner, loser, DuelEnd.EXHAUSTION, context, count, log=log, hits=hits)


def set_footing(rules: Rules, fighter: Fighter, terrain: TerrainKind | None, weather: WeatherKind | None, injuries: int) -> None:
    table = rules.duels
    footing = PERCENT
    if terrain in SLIPPERY:
        footing -= table.terrain_footing
    if weather in WET:
        footing -= table.weather_footing
    footing -= injuries * table.injury_footing
    fighter.footing = max(table.footing_floor, footing)
