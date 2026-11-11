from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import CrowdMoodRow, LearningBiasRow, LearningEventRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import SocialBias
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import towns
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Values, stored_values, write_values
from aerona.engine.mind.values import mean_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int

FEARFUL = (ValueAxis.SUPERSTITION, ValueAxis.DEATH, ValueAxis.PIETY)
ANXIOUS_AT = PERCENT // 2
VALUE_SPAN = 100


@dataclass
class LearningTally:
    learners: int = 0
    prestige: int = 0
    conformity: int = 0
    content: int = 0


async def biases_of(ctx: TickContext, people: EntityRow) -> LearningBiasRow:
    row = await ctx.session.get(LearningBiasRow, people.id)
    if row is None:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
        weights = {
            "prestige_pct": PERCENT + values.get(ValueAxis.HIERARCHY, 0),
            "conformity_pct": PERCENT + values.get(ValueAxis.TRADITION, 0),
            "content_pct": PERCENT // 2 + values.get(ValueAxis.SUPERSTITION, 0) // 2,
        }
        total = max(1, sum(max(0, weight) for weight in weights.values()))
        row = LearningBiasRow(
            holder_entity_id=people.id, locked=[], **{key: clamp_int(max(0, weight) * PERCENT / total, 0, PERCENT) for key, weight in weights.items()}
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


def widest_gap(mine: Values, theirs: Values) -> ValueAxis | None:
    axes = sorted(ValueAxis, key=lambda axis: (-abs(theirs.get(axis, 0) - mine.get(axis, 0)), axis.value))
    return axes[0] if axes and theirs.get(axes[0], 0) != mine.get(axes[0], 0) else None


async def copy(ctx: TickContext, learner: int, mine: Values, axis: ValueAxis, toward: int, *, bias: SocialBias, model: int | None, step: float) -> int:
    gap = toward - mine.get(axis, 0)
    moved = round(max(-step, min(step, gap)))
    if not moved:
        return 0
    mine[axis] = clamp_int(mine.get(axis, 0) + moved, -VALUE_SPAN, VALUE_SPAN)
    await write_values(ctx.session, ValueHolder.PERSONAL, learner, mine)
    ctx.session.add(LearningEventRow(learner_entity_id=learner, model_entity_id=model, bias=bias, axis=axis, shift=moved, epoch=ctx.epoch))
    return moved


async def learn_in(ctx: TickContext, town: EntityRow, tally: LearningTally) -> None:
    table = ctx.rules.social_learning
    people = await people_of(ctx.session, town)
    if people is None:
        return
    biases = await biases_of(ctx, people)
    rows = await ctx.session.execute(
        select(EntityRow.id, MortalProfileRow.renown)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id]))
        .order_by(EntityRow.id)
    )
    folk = [(mortal, renown) for mortal, renown in rows if not held(mortal)]
    if len(folk) < 2:
        return
    rng = ctx.rng(f"learning.{town.id}.{ctx.epoch}")
    learners = [mortal for mortal, _ in folk if rng.chance(table.learners_pct)][: table.learners_cap]
    famous = max(folk, key=lambda pair: (pair[1], -pair[0]))
    majority = await mean_of(ctx.session, ValueHolder.PERSONAL, [mortal for mortal, _ in folk[: table.learners_cap * 2]])
    mood = await ctx.session.get(CrowdMoodRow, town.id)
    fear = table.fear_stickiness / PERCENT if mood is not None and mood.anxiety >= ANXIOUS_AT else 1.0
    for learner in learners:
        mine = dict(await stored_values(ctx.session, ValueHolder.PERSONAL, learner))
        bias = rng.weighted(list(SocialBias), [biases.prestige_pct, biases.conformity_pct, biases.content_pct])
        if bias is SocialBias.PRESTIGE and famous[0] != learner and famous[1] >= table.prestige_floor:
            theirs = await stored_values(ctx.session, ValueHolder.PERSONAL, famous[0])
            axis = widest_gap(mine, theirs)
            if axis is not None and await copy(ctx, learner, mine, axis, theirs.get(axis, 0), bias=bias, model=famous[0], step=table.copy_step):
                tally.prestige += 1
        elif bias is SocialBias.CONFORMITY:
            axis = widest_gap(mine, majority)
            if axis is not None and await copy(ctx, learner, mine, axis, majority.get(axis, 0), bias=bias, model=None, step=table.copy_step):
                tally.conformity += 1
        elif bias is SocialBias.CONTENT:
            axis = rng.pick(FEARFUL)
            pole = VALUE_SPAN if majority.get(axis, 0) >= 0 else -VALUE_SPAN
            if await copy(ctx, learner, mine, axis, pole, bias=bias, model=None, step=table.copy_step * fear):
                tally.content += 1
        tally.learners += 1


async def learn_socially(ctx: TickContext, tally: LearningTally) -> None:
    for town, _ in await towns(ctx):
        if not held(town.id):
            await learn_in(ctx, town, tally)
    await ctx.session.flush()
