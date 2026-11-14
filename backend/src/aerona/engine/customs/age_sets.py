from dataclasses import dataclass
from itertools import pairwise

from sqlalchemy import select

from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import AgeGrade, MarkMeaning
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.context import TickContext
from aerona.engine.customs.marks import MarkTally, customs_of, place
from aerona.engine.customs.naming import NamingTally, initiate_name
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import Namer
from aerona.engine.relations.book import ensure_relation
from aerona.engine.relations.book import shift as shift_relation

GRADES = (AgeGrade.CHILDREN, AgeGrade.YOUTHS, AgeGrade.WARRIORS, AgeGrade.JUNIOR_ELDERS, AgeGrade.SENIOR_ELDERS)


@dataclass
class AgeSetTally:
    opened: int = 0
    initiated: int = 0
    promoted: int = 0
    delayed: int = 0


async def sets_of(ctx: TickContext, people_id: int) -> list[AgeSetRow]:
    return list(await ctx.session.scalars(select(AgeSetRow).where(AgeSetRow.people_entity_id == people_id).order_by(AgeSetRow.initiated_from, AgeSetRow.id)))


async def open_set(ctx: TickContext, people: EntityRow, sets: list[AgeSetRow], tally: AgeSetTally) -> AgeSetRow:
    current = next((row for row in reversed(sets) if row.initiated_to is None), None)
    if current is not None and ctx.epoch - current.initiated_from < ctx.rules.age_sets.span_epochs:
        return current
    if current is not None and "initiated_to" not in current.locked:
        current.initiated_to = ctx.epoch
    row = AgeSetRow(
        people_entity_id=people.id,
        name=f"{people.name} set {len(sets) + 1}",
        initiated_from=ctx.epoch,
        grade=AgeGrade.YOUTHS,
        promoted_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    sets.append(row)
    tally.opened += 1
    return row


async def initiate(ctx: TickContext, people: EntityRow, current: AgeSetRow, tally: AgeSetTally) -> None:
    namer = Namer(ctx.session, ctx.rules)
    marks = await customs_of(ctx, people.id)
    here = await present_among(ctx.session, [people.id])
    members = select(AgeSetMemberRow.mortal_entity_id)
    youths = await ctx.session.scalars(
        select(EntityRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(here, EntityRow.status == EntityStatus.CANON, MortalProfileRow.life_stage == LifeStage.YOUTH, EntityRow.id.not_in(members))
        .order_by(EntityRow.id)
    )
    for mortal in list(youths):
        if held(mortal.id):
            continue
        ctx.session.add(AgeSetMemberRow(mortal_entity_id=mortal.id, age_set_id=current.id, locked=[]))
        await initiate_name(ctx, namer, mortal, NamingTally())
        if MarkMeaning.AGE_SET in marks:
            await place(ctx, mortal, marks[MarkMeaning.AGE_SET], MarkMeaning.AGE_SET, MarkTally())
        tally.initiated += 1


async def bond_mates(ctx: TickContext, row: AgeSetRow) -> None:
    mates = list(
        await ctx.session.scalars(
            select(AgeSetMemberRow.mortal_entity_id).where(AgeSetMemberRow.age_set_id == row.id).order_by(AgeSetMemberRow.mortal_entity_id)
        )
    )
    for first, second in pairwise(mates):
        if held(first) or held(second):
            continue
        relation = await ensure_relation(ctx.session, first, second, ctx.epoch)
        if relation is None:
            continue
        shift_relation(ctx.rules, relation, ctx.epoch, friendship=ctx.rules.age_sets.mates_bond, familiarity=ctx.rules.age_sets.mates_bond)


async def promote(ctx: TickContext, people: EntityRow, sets: list[AgeSetRow], tally: AgeSetTally) -> None:
    for row in sets:
        if row.initiated_to is None or "grade" in row.locked or ctx.epoch - row.promoted_epoch < ctx.rules.age_sets.grade_epochs:
            continue
        index = GRADES.index(row.grade)
        if index >= len(GRADES) - 1:
            continue
        nxt = GRADES[index + 1]
        if nxt is not AgeGrade.SENIOR_ELDERS and any(other.grade is nxt and other.id != row.id for other in sets):
            tally.delayed += 1
            continue
        row.grade, row.promoted_epoch = nxt, ctx.epoch
        tally.promoted += 1
        await bond_mates(ctx, row)
        await note(ctx, f"The {row.name} of the {people.name} rose to the grade of {nxt.value.replace('_', ' ')}.", key="age_sets.promoted", ids=[people.id])


async def keep_age_sets(ctx: TickContext, tally: AgeSetTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        sets = await sets_of(ctx, people.id)
        values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
        if not sets and values.get(ValueAxis.TRADITION, 0) < ctx.rules.age_sets.from_tradition:
            continue
        current = await open_set(ctx, people, sets, tally)
        await initiate(ctx, people, current, tally)
        await promote(ctx, people, sets, tally)
    await ctx.session.flush()
