from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.crafts import AssistiveAidRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.crafts import AssistiveAid
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.crafts.chemistry import knows
from aerona.engine.mortal.learning import practise_subject
from aerona.engine.primitives.naming import seed_of

LENSES = (Technique.ASTRONOMY_INSTRUMENTS,)
FROM_CONDITION = {
    ConditionKind.AGE_BLINDNESS: AssistiveAid.SPECTACLES,
    ConditionKind.AGE_DEAFNESS: AssistiveAid.HEARING_HORN,
    ConditionKind.WITHERED_LIMB: AssistiveAid.CANE,
}
FROM_SKILL = {
    SkillKind.ASTRONOMY: AssistiveAid.TELESCOPE,
    SkillKind.SMITHING: AssistiveAid.MAGNIFIER,
    SkillKind.CARPENTRY: AssistiveAid.MAGNIFIER,
}
GROUND_LENS = frozenset({AssistiveAid.SPECTACLES, AssistiveAid.TELESCOPE, AssistiveAid.MAGNIFIER})
SKILLED = 3


@dataclass
class AidTally:
    fitted: int = 0
    gazed: int = 0


async def needs(ctx: TickContext) -> list[tuple[int, AssistiveAid]]:
    found: list[tuple[int, AssistiveAid]] = []
    conditions = await ctx.session.execute(
        select(ConditionRow.bearer_node_id, ConditionRow.kind)
        .where(ConditionRow.kind.in_(list(FROM_CONDITION)), ConditionRow.ended_epoch.is_(None))
        .order_by(ConditionRow.bearer_node_id)
    )
    found += [(bearer, FROM_CONDITION[kind]) for bearer, kind in conditions]
    skills = await ctx.session.execute(
        select(SkillRow.holder_node_id, SkillRow.skill).where(SkillRow.skill.in_(list(FROM_SKILL)), SkillRow.level >= SKILLED).order_by(SkillRow.holder_node_id)
    )
    found += [(holder, FROM_SKILL[skill]) for holder, skill in skills]
    return found


async def fit(ctx: TickContext, tally: AidTally) -> None:
    table = ctx.rules.aids
    have = {(holder, kind) for holder, kind in await ctx.session.execute(select(AssistiveAidRow.holder_node_id, AssistiveAidRow.kind))}
    for holder_id, kind in await needs(ctx):
        if (holder_id, kind) in have or held(holder_id):
            continue
        mortal = await ctx.session.get(EntityRow, holder_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON or mortal.location_id is None:
            continue
        town = await ctx.session.get(EntityRow, mortal.location_id)
        if town is None or (kind in GROUND_LENS and not await knows(ctx, town, LENSES)):
            continue
        if not ctx.rng(seed_of("aid", holder_id, kind.value, ctx.epoch)).chance(table.fit_chance):
            continue
        ctx.session.add(AssistiveAidRow(holder_node_id=holder_id, kind=kind, since_epoch=ctx.epoch, locked=[]))
        have.add((holder_id, kind))
        tally.fitted += 1


async def gaze(ctx: TickContext, tally: AidTally) -> None:
    xp = ctx.rules.aids.telescope_xp
    for row in list(
        await ctx.session.scalars(select(AssistiveAidRow).where(AssistiveAidRow.kind == AssistiveAid.TELESCOPE).order_by(AssistiveAidRow.holder_node_id))
    ):
        if held(row.holder_node_id):
            continue
        if await practise_subject(
            ctx.session, ctx.rules, row.holder_node_id, SkillKind.ASTRONOMY, subject_id=row.holder_node_id, xp=xp * row.quality / 50, epoch=ctx.epoch
        ):
            tally.gazed += 1


async def keep_aids(ctx: TickContext, tally: AidTally) -> None:
    await fit(ctx, tally)
    await ctx.session.flush()
    await gaze(ctx, tally)
