from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.making_outcomes import MAKING_WEIGHTS
from aerona.catalog.life.minds import MAKING_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import PersonalityValueRow
from aerona.db.tables.minds import MindMakingRow, MindProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.minds import MakingOutcome, MindAffect, MindMaking, MindOrigin, MindPurpose, MindSeat, MindUpkeep, WillCause
from aerona.engine.context import TickContext
from aerona.engine.mind.book import best_skill, clamp_value, values_for
from aerona.engine.minds.phase import change_will
from aerona.engine.minds.profiles import WILL_ORDER, profile_of, will_rank
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.rules.registry import Rules

ORIGINS = {
    MindMaking.CRAFT: MindOrigin.MADE,
    MindMaking.TRAINING: MindOrigin.TRAINED,
    MindMaking.COPYING: MindOrigin.COPIED,
    MindMaking.SUMMONING: MindOrigin.SUMMONED,
    MindMaking.GROWING: MindOrigin.GROWN,
    MindMaking.TRANSFER: MindOrigin.TRANSFERRED,
    MindMaking.AWAKENING: MindOrigin.AWAKENED,
    MindMaking.DIVINE_GRANT: MindOrigin.GRANTED,
}


@dataclass(frozen=True)
class Making:
    method: MindMaking
    seat: MindSeat
    seat_node_id: int | None
    will: MindWill
    purpose: MindPurpose
    affect: MindAffect
    upkeep: MindUpkeep
    skill: int = 0
    works: bool = False


def quality_of(ctx: TickContext, making: Making) -> int:
    table = ctx.rules.mind_making
    return clamp_percent(table.base_quality + round_half_up(making.skill * table.skill_weight_pct / PERCENT) + (table.works_bonus if making.works else 0))


def outcome_of(ctx: TickContext, node_id: int, quality: int) -> MakingOutcome:
    table = ctx.rules.mind_making
    rng = ctx.rng(f"mind.making.{node_id}.{ctx.epoch}")
    if quality >= table.failure_below:
        return MakingOutcome.EXCEEDED if quality >= PERCENT and rng.chance(table.exceeded_pct) else MakingOutcome.AS_MEANT
    if not rng.chance((table.failure_below - quality) * PERCENT / max(1, table.failure_below)):
        return MakingOutcome.AS_MEANT
    weights = {outcome: int(getattr(table, rule_name)) for outcome, rule_name in MAKING_WEIGHTS.items() if rule_name is not None}
    return rng.weighted_by(list(weights), lambda item: weights[item])


async def inherit_values(ctx: TickContext, node_id: int, maker_id: int | None) -> int:
    if maker_id is None:
        return 0
    noise = ctx.rules.mind_making.value_noise
    rng = ctx.rng(f"mind.values.{node_id}.{ctx.epoch}")
    known = {row.axis for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id == node_id))}
    written = 0
    for axis, value in sorted((await values_for(ctx.session, maker_id)).items(), key=lambda item: item[0].value):
        if axis in known:
            continue
        ctx.session.add(PersonalityValueRow(node_id=node_id, axis=axis, value=clamp_value(value + rng.die(noise * 2 + 1) - noise - 1)))
        written += 1
    return written


def apply_outcome(ctx: TickContext, row: MindProfileRow, outcome: MakingOutcome, meant: MindWill) -> None:
    if outcome is MakingOutcome.UNSTABLE and "stability" not in row.locked:
        row.stability = clamp_percent(row.stability // 3)
    elif outcome is MakingOutcome.EMPTY_SEAT:
        change_will(ctx, row, MindWill.NONE, WillCause.DAMAGE)
        if "affect" not in row.locked:
            row.affect = MindAffect.NONE
    elif outcome is MakingOutcome.EXCEEDED and "capacity" not in row.locked:
        row.capacity = clamp_percent(row.capacity + ctx.rules.mind_making.exceeded_capacity)
    elif outcome is MakingOutcome.UNINTENDED_WILL:
        shift = 1 if ctx.rng(f"mind.unintended.{row.node_id}.{ctx.epoch}").chance(PERCENT // 2) else -1
        change_will(ctx, row, WILL_ORDER[max(0, min(len(WILL_ORDER) - 2, will_rank(meant) + shift))], WillCause.DAMAGE)


async def missing_craft(session: AsyncSession, rules: Rules, maker_id: int, method: MindMaking) -> str | None:
    if method not in MAKING_SKILLS:
        return "only a god can grant a mind"
    if await best_skill(session, maker_id, MAKING_SKILLS[method]) < rules.mind_making.skill_floor:
        return "the maker lacks the craft this way of making calls for"
    return None


async def make_mind(ctx: TickContext, node_id: int, maker_id: int | None, making: Making) -> MindProfileRow:
    row = await profile_of(ctx.session, ctx.rules, node_id, ctx.epoch)
    quality = quality_of(ctx, making)
    capacity = clamp_percent(round_half_up(quality * PERCENT / max(1, ctx.rules.minds.baseline_capacity * 2)))
    maker = await ctx.session.get(EntityRow, maker_id) if maker_id is not None else None
    if making.method is not MindMaking.DIVINE_GRANT and (maker is None or maker.entity_type is not EntityType.POLITY):
        capacity = min(capacity, ctx.rules.mind_making.programme_capacity)
    values = {
        "seat": making.seat,
        "seat_node_id": making.seat_node_id,
        "origin": ORIGINS[making.method],
        "affect": making.affect,
        "purpose": making.purpose,
        "upkeep": making.upkeep,
        "capacity": capacity,
        "stability": clamp_percent(quality + PERCENT // 2),
        "made_by_node_id": maker_id,
    }
    for key, value in values.items():
        if key not in row.locked:
            setattr(row, key, value)
    change_will(ctx, row, making.will, WillCause.CAPACITY)
    outcome = outcome_of(ctx, node_id, quality)
    apply_outcome(ctx, row, outcome, making.will)
    ctx.session.add(MindMakingRow(mind_node_id=node_id, maker_node_id=maker_id, method=making.method, quality=quality, outcome=outcome, epoch=ctx.epoch))
    await inherit_values(ctx, node_id, maker_id)
    if maker_id is not None and maker_id != node_id:
        await connect(ctx.session, maker_id, node_id, BondKind.MADE_MIND_OF, ctx.epoch, description="made its mind")
    await ctx.session.flush()
    return row
