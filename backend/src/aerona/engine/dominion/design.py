from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.dominion import DOMAIN_SCALES, FAVOURED_POLE
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.dominion import SCALE_MAX, SCALE_MIN, GodDesignRow, GodScaleRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.rarity import Rarity
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules


@dataclass
class Design:
    dominion_strength: int = 0
    magic_aptitude: int = 0
    manifestation_strength: int = 0
    scales: dict[DivineScale, int] = field(default_factory=dict)
    powers: int = 0


@dataclass(frozen=True)
class Checked:
    design: Design
    budget: int
    spent: int
    stats_pct: int


def budget_of(rules: Rules, rarity: Rarity, stars: int) -> int:
    table = rules.god_design
    return (rarity.rank + 1) * table.budget_per_rank + stars * table.budget_per_star


def scale_cost(rules: Rules, scale: DivineScale, value: int) -> int:
    return value * FAVOURED_POLE[scale] * rules.god_design.scale_cost


def cost_of(rules: Rules, design: Design) -> int:
    table = rules.god_design
    parts = (
        design.dominion_strength * table.dominion_cost_pct / PERCENT
        + design.magic_aptitude * table.magic_cost_pct / PERCENT
        + design.manifestation_strength * table.manifestation_cost_pct / PERCENT
        + design.powers * table.power_cost
        + sum(scale_cost(rules, scale, value) for scale, value in design.scales.items())
    )
    return max(0, round_half_up(parts))


def trimmed(design: Design, share: float) -> Design:
    return Design(
        dominion_strength=round_half_up(design.dominion_strength * share),
        magic_aptitude=round_half_up(design.magic_aptitude * share),
        manifestation_strength=round_half_up(design.manifestation_strength * share),
        scales={scale: value if FAVOURED_POLE[scale] * value <= 0 else round_half_up(value * share) for scale, value in design.scales.items()},
        powers=design.powers,
    )


def fate_check(rules: Rules, budget: int, design: Design) -> Checked:
    proposed = Design(
        dominion_strength=clamp_int(design.dominion_strength, 0, PERCENT),
        magic_aptitude=clamp_int(design.magic_aptitude, 0, PERCENT),
        manifestation_strength=clamp_int(design.manifestation_strength, 0, PERCENT),
        scales={scale: clamp_int(value, SCALE_MIN, SCALE_MAX) for scale, value in design.scales.items()},
        powers=design.powers,
    )
    spent = cost_of(rules, proposed)
    if spent > budget and spent > 0:
        proposed = trimmed(proposed, max(0.0, budget / spent))
        spent = min(budget, cost_of(rules, proposed))
    floor = rules.god_design.stats_floor_pct
    left = max(0, budget - spent)
    stats_pct = clamp_int(floor + (PERCENT - floor) * left / budget, floor, PERCENT) if budget else PERCENT
    return Checked(proposed, budget, spent, stats_pct)


def aspect_scales(domains: tuple[Domain, ...]) -> dict[DivineScale, int]:
    found: dict[DivineScale, int] = {}
    for domain in domains:
        for scale, step in DOMAIN_SCALES[domain]:
            found[scale] = clamp_int(found.get(scale, 0) + step, SCALE_MIN, SCALE_MAX)
    return found


async def write_design(session: AsyncSession, god_id: int, checked: Checked, epoch: int) -> GodDesignRow:
    row = await session.get(GodDesignRow, god_id)
    if row is None:
        row = GodDesignRow(god_node_id=god_id, locked=[])
        session.add(row)
    values = {
        "budget": checked.budget,
        "spent": checked.spent,
        "dominion_strength": checked.design.dominion_strength,
        "magic_aptitude": checked.design.magic_aptitude,
        "manifestation_strength": checked.design.manifestation_strength,
        "stats_pct": checked.stats_pct,
        "checked_epoch": epoch,
    }
    for key, value in values.items():
        if key not in row.locked:
            setattr(row, key, value)
    for scale, value in checked.design.scales.items():
        found = await session.get(GodScaleRow, (god_id, scale))
        if found is None:
            session.add(GodScaleRow(god_node_id=god_id, scale=scale, value=value, locked=[]))
        elif "value" not in found.locked:
            found.value = value
    await session.flush()
    return row


async def ensure_designs(session: AsyncSession, rules: Rules, epoch: int) -> int:
    made = 0
    known = set(await session.scalars(select(GodDesignRow.god_node_id)))
    for son in await session.scalars(select(SonRow).order_by(SonRow.id)):
        if son.id in known or held(son.id):
            continue
        design = Design(
            dominion_strength=son.might, magic_aptitude=son.wisdom, manifestation_strength=son.endurance, scales=aspect_scales(son.domains), powers=0
        )
        await write_design(session, son.id, fate_check(rules, budget_of(rules, son.rarity, son.stars), design), epoch)
        made += 1
    creator = await session.scalar(select(CreatorRow).limit(1))
    if creator is not None and creator.id not in known and not held(creator.id):
        design = Design(dominion_strength=PERCENT // 2, magic_aptitude=PERCENT // 2, manifestation_strength=PERCENT // 2)
        await write_design(session, creator.id, fate_check(rules, max(cost_of(rules, design), 1), design), epoch)
        made += 1
    for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        if god.id in known or held(god.id):
            continue
        domains = tuple(domain for domain in (god.domain_primary, god.domain_secondary) if domain is not None)
        design = Design(dominion_strength=god.power, magic_aptitude=god.wisdom, manifestation_strength=god.endurance, scales=aspect_scales(domains))
        budget = max(cost_of(rules, design), 1)
        await write_design(session, god.id, fate_check(rules, budget, design), epoch)
        made += 1
    return made


def scaled_stats(values: dict[str, int], stats_pct: int) -> dict[str, int]:
    return {key: max(1, round_half_up(value * stats_pct / PERCENT)) for key, value in values.items()}
