from dataclasses import dataclass

from aerona.catalog import god_lines
from aerona.catalog.powers import POWERS, power_unlock_levels
from aerona.catalog.rarities import build_rarity_table
from aerona.catalog.stats import max_essence, max_hp
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.son import Stat
from aerona.domain.models.stats import STAT_CEILING, STAT_FLOOR
from aerona.engine.context import TickContext
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class LevelUp:
    level: int
    first: Stat
    second: Stat
    first_gain: int
    second_gain: int
    awakened: str | None


@dataclass(frozen=True)
class Progress:
    level_ups: tuple[LevelUp, ...] = ()


@dataclass(frozen=True)
class StarRequirement:
    stars: int
    level: int
    fame: int
    essence: int


def clamp_stat(value: float) -> int:
    return max(STAT_FLOOR, min(STAT_CEILING, round(value)))


def son_max_hp(rules: Rules, son: SonRow) -> int:
    return max_hp(rules, son.endurance)


def son_max_essence(rules: Rules, son: SonRow) -> int:
    return max_essence(rules, son.might)


def clamp_son(rules: Rules, son: SonRow) -> SonRow:
    son.hp = max(0, min(son.hp, son_max_hp(rules, son)))
    son.essence = max(0, min(son.essence, son_max_essence(rules, son)))
    son.existence = max(PERCENT_MIN, min(PERCENT_MAX, son.existence))
    return son


def xp_for_next_level(rules: Rules, level: int) -> int:
    return rules.core_rules.xp_per_level * level


def power_ceiling(rules: Rules, son: SonRow) -> int:
    return build_rarity_table(rules)[son.rarity].power_cap + (son.stars - 1) // max(1, rules.core_rules.stars_per_power_cap)


def star_requirement(rules: Rules, target: int) -> StarRequirement:
    core = rules.core_rules
    return StarRequirement(
        target, target * core.star_level_step - 1, (target - 1) * core.star_renown_step, core.star_essence_base + target * core.star_essence_step
    )


def cap_gained_essence(rules: Rules, son: SonRow, before: int) -> None:
    son.essence = min(son.essence, max(before, son_max_essence(rules, son)))


async def grant_progress(ctx: TickContext, son: SonRow, *, xp: int, fame: int) -> Progress:
    rules = ctx.rules
    son.xp += max(0, xp)
    son.fame += max(0, fame)
    powers = {power.slot: power for power in await SonRepository(ctx.session).powers(son.id)}
    unlocks = power_unlock_levels(rules)
    stats = list(Stat)
    rng = ctx.rng(f"level.{son.id}")
    gains = (rules.son_tools.level_up_stat_1, rules.son_tools.level_up_stat_2)
    level_ups: list[LevelUp] = []
    while son.xp >= xp_for_next_level(rules, son.level):
        son.xp -= xp_for_next_level(rules, son.level)
        son.level += 1
        first, second = rng.pick(stats), rng.pick(stats)
        setattr(son, first.value, clamp_stat(son.stat(first) + gains[0]))
        setattr(son, second.value, clamp_stat(son.stat(second) + gains[1]))
        line = god_lines.SON_LEVEL_UP
        await ctx.chronicle(ChronicleKind.SYSTEM, line.render(son=son.name, level=son.level), template_key=line.key, son_id=son.id)
        awakened: str | None = None
        for slot, level in enumerate(unlocks):
            power = powers.get(slot)
            if level == son.level and power is not None:
                awakened = power.name or POWERS[power.effect].name
                awoke = god_lines.SON_POWER_AWOKE
                await ctx.chronicle(ChronicleKind.SYSTEM, awoke.render(son=son.name, power=awakened), template_key=awoke.key, son_id=son.id)
        level_ups.append(LevelUp(son.level, first, second, gains[0], gains[1], awakened))
    clamp_son(rules, son)
    await ctx.session.flush()
    return Progress(tuple(level_ups))
