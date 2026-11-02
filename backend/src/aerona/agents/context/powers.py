from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.powers import POWERS
from aerona.catalog.stats import STATS
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import PowerLine, PowersContext
from aerona.rules.registry import Rules


def unlock_levels(rules: Rules) -> tuple[int, int, int]:
    levels = rules.power_unlock_levels
    return (levels.power_1_unlock_level, levels.power_2_unlock_level, levels.power_3_unlock_level)


def unlocked(rules: Rules, son: SonRow, power: SonPowerRow) -> bool:
    levels = unlock_levels(rules)
    return son.level >= levels[min(power.slot, len(levels) - 1)]


def effect_text(rules: Rules, power: SonPowerRow) -> str:
    text = POWERS[power.effect].describe(rules)
    if power.param_entity_type is not None:
        return f"{text} (chosen type: {ENTITY_TYPES[power.param_entity_type].label})"
    if power.param_stat is not None:
        return f"{text} (chosen stat: {STATS[power.param_stat].label})"
    return text


def power_lines(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> list[PowerLine]:
    levels = unlock_levels(rules)
    return [
        PowerLine(
            name=power.name,
            effect_text=effect_text(rules, power),
            unlock_level=None if unlocked(rules, son, power) else levels[min(power.slot, len(levels) - 1)],
            description=power.description,
        )
        for power in sorted(powers, key=lambda item: item.slot)
    ]


def powers_text(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> str:
    return render(PromptId.POWERS, PowersContext(powers=power_lines(rules, son, powers)))
