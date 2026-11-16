from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.powers import POWERS
from aerona.catalog.stats import STATS
from aerona.core.grammar import spoken
from aerona.db.tables.divine_powers import DivinePowerRow
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


async def divine_power_lines(session: AsyncSession, holder_id: int, epoch: int) -> list[str]:
    rows = await session.scalars(select(DivinePowerRow).where(DivinePowerRow.holder_node_id == holder_id).order_by(DivinePowerRow.id))
    found = []
    for row in rows:
        key = f" ({row.object_key.replace('_', ' ')})" if row.object_key else ""
        ready = row.last_used_epoch is None or epoch - row.last_used_epoch >= row.cooldown
        state = "ready" if ready else f"resting until epoch {(row.last_used_epoch or 0) + row.cooldown}"
        found.append(
            f"{row.name} (power_id {row.id}): {spoken(row.verb)} {row.object.value.replace('_', ' ')}{key}, reaching {spoken(row.scope)}, "
            f"acting {spoken(row.mode)}, strength {row.strength}, costing {row.cost_amount} {spoken(row.cost)}; {state}"
        )
    return found
