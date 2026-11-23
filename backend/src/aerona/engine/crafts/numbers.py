from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.crafts import SCHOOLING
from aerona.catalog.life_traits import TECHNIQUE_TRAITS, having
from aerona.catalog.notations import NOTATIONS
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import UNTAUGHT_NUMERACY, NumberSystemRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import Notation, NumberMilestone
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import TechniqueTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique, techniques_of
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import StepDraft, record

BASES = (10, 12, 20, 60)
PLACE_VALUE_RECKONING = having(TECHNIQUE_TRAITS, TechniqueTrait.PLACE_VALUE_RECKONING)


@dataclass
class NumberTally:
    read: int = 0
    taught: int = 0
    milestones: int = 0
    notations: int = 0


async def seed_system(ctx: TickContext, people: EntityRow, tally: NumberTally) -> NumberSystemRow:
    row = await ctx.session.get(NumberSystemRow, people.id)
    if row is not None:
        return row
    rng = ctx.rng(seed_of("numbers", people.id))
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    known = await techniques_of(ctx.session, people.id)
    placed = bool(known & PLACE_VALUE_RECKONING)
    written = Technique.ALPHABET in known or (culture is not None and culture.literacy > 0)
    row = NumberSystemRow(
        people_entity_id=people.id,
        base=rng.pick(list(BASES)),
        notation=Notation.POSITIONAL if placed else (Notation.ADDITIVE if written else Notation.TALLY),
        zero=placed,
        numeracy=max(UNTAUGHT_NUMERACY, culture.literacy if culture is not None else 0),
        locked=[],
    )
    ctx.session.add(row)
    tally.read += 1
    return row


async def symbolic_ready(ctx: TickContext, people_id: int) -> bool:
    levels = (await known_levels(ctx.session, [people_id])).get(people_id, {})
    return levels.get(KnowledgeBranch.MATHEMATICS, 0) >= ctx.rules.numeracy.symbolic_level


async def adopt(ctx: TickContext, people: EntityRow, row: NumberSystemRow, notation: Notation, tally: NumberTally) -> None:
    before = row.notation
    row.notation = notation
    tally.notations += 1
    await record(
        ctx,
        "numeracy.notation_adopted",
        roles={IncidentRole.SUBJECT: people.id},
        facts={"notation": notation, "before": before, "rank": NOTATIONS[notation].rank},
        steps=(StepDraft(StepAction.LEARN, actor=people.id, outcome=StepOutcome.SUCCESS),),
    )


async def keep_numbers(ctx: TickContext, tally: NumberTally) -> None:
    table = ctx.rules.numeracy
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        row = await seed_system(ctx, people, tally)
        schooled = any([await has_technique(ctx.session, people.id, technique) for technique in SCHOOLING])
        if schooled and "numeracy" not in row.locked:
            row.numeracy = clamp_int(row.numeracy + table.numeracy_gain, 0, PERCENT)
            tally.taught += 1
        if row.notation is Notation.TALLY and "notation" not in row.locked and await has_technique(ctx.session, people.id, Technique.ALPHABET):
            await adopt(ctx, people, row, Notation.ADDITIVE, tally)
        if not await has_technique(ctx.session, people.id, Technique.LOGIC):
            continue
        if not ctx.rng(seed_of("numbers.milestone", people.id, ctx.epoch)).chance(table.milestone_chance):
            continue
        if not row.zero and "zero" not in row.locked:
            row.zero = True
            found = NumberMilestone.ZERO
        elif row.notation is Notation.ADDITIVE and "notation" not in row.locked:
            await adopt(ctx, people, row, Notation.POSITIONAL, tally)
            found = NumberMilestone.PLACE_VALUE
        elif row.notation is Notation.POSITIONAL and "notation" not in row.locked and await symbolic_ready(ctx, people.id):
            await adopt(ctx, people, row, Notation.SYMBOLIC, tally)
            continue
        else:
            continue
        if "numeracy" not in row.locked:
            row.numeracy = clamp_int(row.numeracy + table.milestone_pct, 0, PERCENT)
        tally.milestones += 1
        await record(
            ctx,
            "numbers.milestone",
            roles={IncidentRole.SUBJECT: people.id},
            facts={"milestone": found, "base": row.base, "numeracy": row.numeracy},
            steps=(StepDraft(StepAction.DISCOVER, actor=people.id, outcome=StepOutcome.SUCCESS),),
        )
    await ctx.session.flush()
