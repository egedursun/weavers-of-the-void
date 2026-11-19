from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import UNTAUGHT_NUMERACY, NumberSystemRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import Notation, NumberMilestone
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique, techniques_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import StepDraft, record

BASES = (10, 12, 20, 60)
SCHOOLING = (Technique.ALPHABET, Technique.BUREAUCRACY, Technique.UNIVERSITIES, Technique.DOUBLE_ENTRY)
PLACE_VALUE_RECKONING = frozenset({Technique.DOUBLE_ENTRY, Technique.COMPUTATION})


@dataclass
class NumberTally:
    read: int = 0
    taught: int = 0
    milestones: int = 0


async def seed_system(ctx: TickContext, people: EntityRow, tally: NumberTally) -> NumberSystemRow:
    row = await ctx.session.get(NumberSystemRow, people.id)
    if row is not None:
        return row
    rng = ctx.rng(seed_of("numbers", people.id))
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    placed = bool(await techniques_of(ctx.session, people.id) & PLACE_VALUE_RECKONING)
    row = NumberSystemRow(
        people_entity_id=people.id,
        base=rng.pick(list(BASES)),
        notation=Notation.POSITIONAL if placed else Notation.ADDITIVE,
        zero=placed,
        numeracy=max(UNTAUGHT_NUMERACY, culture.literacy if culture is not None else 0),
        locked=[],
    )
    ctx.session.add(row)
    tally.read += 1
    return row


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
        if not await has_technique(ctx.session, people.id, Technique.LOGIC):
            continue
        if not ctx.rng(seed_of("numbers.milestone", people.id, ctx.epoch)).chance(table.milestone_chance):
            continue
        if not row.zero and "zero" not in row.locked:
            row.zero = True
            found = NumberMilestone.ZERO
        elif row.notation is Notation.ADDITIVE and "notation" not in row.locked:
            row.notation = Notation.POSITIONAL
            found = NumberMilestone.PLACE_VALUE
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
