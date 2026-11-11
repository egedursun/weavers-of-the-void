from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.arcana import DURATION_EPOCHS, DURATION_STEP, FORM_COST, RANGE_STEP, SCHOOL_GRAMMAR, TARGET_STEP, TECHNIQUE_COST
from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Shape:
    technique: SpellTechnique
    form: SpellForm
    range: SpellRange = SpellRange.SIGHT
    duration: SpellDuration = SpellDuration.INSTANT
    target: SpellTarget = SpellTarget.ONE


def difficulty_of(rules: Rules, shape: Shape, power: int) -> int:
    return (
        TECHNIQUE_COST[shape.technique]
        + FORM_COST[shape.form]
        + RANGE_STEP[shape.range]
        + DURATION_STEP[shape.duration]
        + TARGET_STEP[shape.target]
        + power * rules.spell_grammar.difficulty_per_power
    )


def shape_of(row: RiteGrammarRow) -> Shape:
    return Shape(row.technique, row.form, row.range, row.duration, row.target)


async def ensure_grammar(session: AsyncSession, rules: Rules, profile: RiteProfileRow) -> RiteGrammarRow:
    row = await session.get(RiteGrammarRow, profile.rite_entity_id)
    if row is not None:
        return row
    technique, form = SCHOOL_GRAMMAR[profile.school]
    shape = Shape(technique, form)
    row = RiteGrammarRow(
        rite_entity_id=profile.rite_entity_id,
        technique=technique,
        form=form,
        range=shape.range,
        duration=shape.duration,
        target=shape.target,
        difficulty=difficulty_of(rules, shape, profile.power),
        locked=[],
    )
    session.add(row)
    await session.flush()
    return row


async def write_grammar(
    session: AsyncSession, rules: Rules, profile: RiteProfileRow, shape: Shape, *, paradigm_id: int | None, myth_id: int | None
) -> RiteGrammarRow:
    row = await ensure_grammar(session, rules, profile)
    row.technique, row.form, row.range, row.duration, row.target = shape.technique, shape.form, shape.range, shape.duration, shape.target
    row.paradigm_entity_id, row.myth_entity_id = paradigm_id, myth_id
    row.difficulty = difficulty_of(rules, shape, profile.power)
    await session.flush()
    return row


def cost_factor(rules: Rules, row: RiteGrammarRow) -> float:
    return 1 + row.difficulty * rules.spell_grammar.cost_per_difficulty_pct / PERCENT


def backlash_factor(rules: Rules, row: RiteGrammarRow) -> float:
    return 1 + row.difficulty * rules.spell_grammar.backlash_per_difficulty_pct / PERCENT


def window_of(row: RiteGrammarRow | None) -> int:
    return DURATION_EPOCHS[row.duration] if row is not None else 1


def reaches(atlas: RegionAtlas, row: RiteGrammarRow, caster: EntityRow, target: EntityRow | None) -> bool:
    if target is None or row.range is SpellRange.WORLD:
        return target is None or target.world_id == caster.world_id
    if row.range is SpellRange.TOUCH:
        return target.id in {caster.id, caster.location_id} or target.location_id in {caster.id, caster.location_id}
    home, there = atlas.top_region(caster.id), atlas.top_region(target.id)
    if row.range is SpellRange.REGION and home is not None:
        return there in {home, *atlas.neighbour_regions(home)}
    return there == home


async def ensure_all(ctx: TickContext) -> int:
    known = set(await ctx.session.scalars(select(RiteGrammarRow.rite_entity_id)))
    made = 0
    for profile in list(await ctx.session.scalars(select(RiteProfileRow).order_by(RiteProfileRow.rite_entity_id))):
        if profile.rite_entity_id in known or held(profile.rite_entity_id):
            continue
        await ensure_grammar(ctx.session, ctx.rules, profile)
        made += 1
    return made
