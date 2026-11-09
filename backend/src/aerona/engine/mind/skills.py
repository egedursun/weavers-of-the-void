from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CAREER_SKILLS, CAREER_VALUES, FIXED_ROLES, ROLE_SKILLS, SKILLS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.mind import SKILL_MAX, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mind import Attribute, CareerChange, MemoryKind, SkillKind, SkillSource, ThoughtKind, TraitEffect, ValueAxis
from aerona.engine.body.book import factor
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import colour_factor
from aerona.engine.mind.aspirations import focus_rate, open_wants, steered_values
from aerona.engine.mind.book import SKILLS_KEY, clamp_skill, effect_of, is_locked, mind_of, scaled_by, set_skill, skills_of, values_for
from aerona.engine.mind.memories import remember
from aerona.engine.mind.space import blend
from aerona.engine.mind.split import effective_attributes, governing, talent
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.traits import teach_trait
from aerona.engine.mortal.variants import learning, variants_by_id
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules

SKILL_LOCK = "skills"
ROLE_LOCK = "role"
STAT_MIDPOINT = 50


@dataclass(frozen=True)
class CareerMove:
    old: MortalRole
    new: MortalRole
    reason: CareerChange


def seed_level(rules: Rules, mortal: EntityRow, skill: SkillKind, base: int, rng: SeededRandom, *, attributes: Mapping[Attribute, int]) -> int:
    table = rules.skills
    age = stat_or(mortal, "age", table.adult_age)
    lifespan = stat(mortal, "lifespan") or 0
    youth = min(1.0, age / table.adult_age) if table.adult_age else 1.0
    experience = min(table.seed_age_cap, max(0, age - table.adult_age) * table.seed_age_gain / PERCENT)
    talent = (governing(attributes, skill) - STAT_MIDPOINT) * table.seed_stat_pct / PERCENT
    level = (base + talent + experience) * youth + rng.integer(-table.seed_jitter, table.seed_jitter)
    if lifespan and SKILLS[skill].physical and age > lifespan * table.decline_start_pct / PERCENT:
        level -= table.decline_per_epoch
    return clamp_skill(level)


async def seed_skills(session: AsyncSession, rules: Rules, mortal: EntityRow, rng: SeededRandom, epoch: int) -> int:
    if await skills_of(session, mortal.id):
        return 0
    role = mortal.mortal_role or MortalRole.COMMONER
    seeded = 0
    attributes = await effective_attributes(session, rules, mortal)
    for skill, base in ROLE_SKILLS.get(role, ROLE_SKILLS[MortalRole.COMMONER]).items():
        level = seed_level(rules, mortal, skill, base, rng, attributes=attributes)
        if level > 0:
            await set_skill(session, mortal.id, skill, level, epoch=epoch, source=SkillSource.BACKFILL)
            seeded += 1
    return seeded


def level_cost(rules: Rules, level: int) -> int:
    table = rules.skills
    return max(1, round(table.xp_per_level * (PERCENT + level * table.level_cost_growth_pct) / PERCENT))


async def practise(
    session: AsyncSession, rules: Rules, node_id: int, skill: SkillKind, xp: float, *, epoch: int, source: SkillSource = SkillSource.PRACTICE
) -> int:
    if xp <= 0 or write_blocked(node_id, SKILLS_KEY):
        return 0
    mind = await mind_of(session, node_id)
    if is_locked(mind, SKILL_LOCK):
        return 0
    rows = await skills_of(session, node_id)
    row = rows.get(skill)
    if row is None:
        row = await set_skill(session, node_id, skill, 0, epoch=epoch, source=source)
    rate = scaled_by(await effect_of(session, node_id, TraitEffect.LEARNING, rules.traits.effect_scale_pct))
    holder = await session.get(EntityRow, node_id)
    if holder is not None:
        rate *= talent(rules, await effective_attributes(session, rules, holder), skill)
        rate *= colour_factor(rules, await session.get(GenomeRow, node_id), skill)
        rate *= await focus_rate(session, rules, node_id, skill)
    rate *= learning(await variants_by_id(session, [row.variant_id]), row.variant_id)
    schooled = await session.get(MortalProfileRow, node_id)
    if schooled is not None:
        rate *= 1 + schooled.education / PERCENT * rules.education.education_skill_pct / PERCENT
    if row.level < row.peak:
        rate *= rules.skills.relearn_pct / PERCENT
    row.xp += round(xp * rate)
    gained = 0
    while row.level < SKILL_MAX and row.xp >= level_cost(rules, row.level):
        row.xp -= level_cost(rules, row.level)
        row.level += 1
        gained += 1
    row.peak = max(row.peak, row.level)
    row.last_used_epoch = epoch
    await session.flush()
    return gained


async def practise_any(session: AsyncSession, rules: Rules, node_id: int, skills: Iterable[SkillKind], xp: float, *, epoch: int) -> int:
    rows = await skills_of(session, node_id)
    wanted = list(skills)
    best = max(wanted, key=lambda skill: (rows[skill].level if skill in rows else -1, -wanted.index(skill)))
    return await practise(session, rules, node_id, best, xp, epoch=epoch)


async def weather_skills(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.skills
    if is_locked(await mind_of(ctx.session, mortal.id), SKILL_LOCK):
        return 0
    age = stat(mortal, "age") or 0
    lifespan = stat(mortal, "lifespan") or 0
    old = lifespan > 0 and age > lifespan * table.decline_start_pct / PERCENT
    changed = 0
    for row in (await skills_of(ctx.session, mortal.id)).values():
        before = row.level
        if ctx.epoch - row.last_used_epoch >= table.rust_epochs:
            floor = round(row.peak * table.rust_floor_pct / PERCENT)
            row.level = max(min(row.level, floor), round(row.level * (PERCENT - table.rust_rate_pct) / PERCENT))
        if old and SKILLS[row.skill].physical:
            row.level = clamp_skill(row.level - table.decline_per_epoch)
        changed += 1 if row.level != before else 0
    await ctx.session.flush()
    return changed


async def shared_tongue(ctx: TickContext, master: EntityRow, student: EntityRow) -> float:
    tongues = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[student.id])]
    if not tongues:
        return 1.0
    floor = ctx.rules.skills.foreign_teaching_pct / PERCENT
    rows = await ctx.session.scalars(
        select(SkillRow.level).where(SkillRow.holder_node_id == master.id, SkillRow.skill == SkillKind.LANGUAGES, SkillRow.subject_node_id.in_(tongues))
    )
    spoken = await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[master.id], targets=tongues)
    best = PERCENT if spoken else max(rows, default=0)
    return floor + (1 - floor) * best / PERCENT


async def teach_apprentices(ctx: TickContext) -> int:
    table = ctx.rules.skills
    taught = 0
    for bond in await active_bonds(ctx.session, [BondKind.APPRENTICE_OF]):
        student = await living_entity(ctx.session, bond.source_node_id)
        master = await living_entity(ctx.session, bond.target_node_id)
        if student is None or master is None or student.entity_type is not EntityType.MORTAL or master.entity_type is not EntityType.MORTAL:
            continue
        lessons = sorted((await skills_of(ctx.session, master.id)).values(), key=lambda row: (-row.level, row.skill))[: table.taught_skills]
        teaching = (await skills_of(ctx.session, master.id)).get(SkillKind.TEACHING)
        quality = (PERCENT + (teaching.level if teaching is not None else 0)) / PERCENT
        quality *= await shared_tongue(ctx, master, student)
        for lesson in lessons:
            student_level = (await skills_of(ctx.session, student.id)).get(lesson.skill)
            if student_level is not None and student_level.level >= lesson.level:
                continue
            gap = lesson.level - (student_level.level if student_level is not None else 0)
            pace = 1 + gap * table.teach_gap_pct / PERCENT / PERCENT
            keen = await ctx.hook_factor(student.id, DomainHook.LEARNING)
            await practise(
                ctx.session, ctx.rules, student.id, lesson.skill, table.teach_xp * quality * pace * keen, epoch=ctx.epoch, source=SkillSource.TEACHING
            )
        await practise(ctx.session, ctx.rules, master.id, SkillKind.TEACHING, table.teaching_xp, epoch=ctx.epoch)
        await think(ctx.session, ctx.rules, master.id, ThoughtKind.TAUGHT_APPRENTICE, ctx.epoch, subject_id=student.id)
        await remember(
            ctx.session, ctx.rules, holder_id=student.id, subject_id=master.id, kind=MemoryKind.TAUGHT_ME, magnitude=table.taught_memory, epoch=ctx.epoch
        )
        await teach_trait(ctx, student.id, master.id)
        taught += 1
    return taught


async def role_levels(session: AsyncSession, mortal_id: int, rows: Mapping[SkillKind, SkillRow]) -> dict[MortalRole, tuple[int, int]]:
    levels: dict[MortalRole, tuple[int, int]] = {}
    for role, skills in CAREER_SKILLS.items():
        raw = max((rows[skill].level for skill in skills if skill in rows), default=0)
        effective = 0
        for skill in skills:
            if skill in rows:
                effective = max(effective, round(rows[skill].level * await factor(session, mortal_id, SKILLS[skill].capacity)))
        levels[role] = (raw, effective)
    return levels


def career_score(rules: Rules, role: MortalRole, effective: int, values: Mapping[ValueAxis, int]) -> float:
    lean = sum(values.get(axis, 0) * weight for axis, weight in CAREER_VALUES.get(role, {}).items()) / PERCENT
    return effective + lean * rules.careers.values_weight_pct / PERCENT


async def career_open(ctx: TickContext, mortal: EntityRow) -> dict[SkillKind, SkillRow] | None:
    role = mortal.mortal_role
    if role is None or role in FIXED_ROLES or is_locked(await mind_of(ctx.session, mortal.id), ROLE_LOCK):
        return None
    rows = await skills_of(ctx.session, mortal.id)
    return rows or None


def career_move(rules: Rules, role: MortalRole, levels: dict[MortalRole, tuple[int, int]], values: Mapping[ValueAxis, int]) -> CareerMove | None:
    table = rules.careers
    current_raw, current_effective = levels.get(role, (0, 0))
    injured = role in CAREER_SKILLS and current_raw >= table.min_level and current_effective * PERCENT < current_raw * table.end_pct
    candidates = {
        other: career_score(rules, other, effective, values) for other, (_, effective) in levels.items() if other is not role and effective >= table.min_level
    }
    best = max(sorted(candidates), key=lambda other: candidates[other], default=None)
    if injured:
        return CareerMove(role, best if best is not None else MortalRole.COMMONER, CareerChange.INJURED)
    current_score = career_score(rules, role, current_effective, values) if role in CAREER_SKILLS else 0
    if best is not None and candidates[best] >= current_score + table.switch_margin:
        return CareerMove(role, best, CareerChange.SKILLED)
    return None


async def choose_career(ctx: TickContext, mortal: EntityRow, values: Mapping[ValueAxis, int]) -> CareerMove | None:
    rows = await career_open(ctx, mortal)
    if rows is None or mortal.mortal_role is None:
        return None
    people = await people_of(ctx.session, mortal)
    culture = await values_for(ctx.session, people.id) if people is not None else {}
    steered = blend(values, culture, ctx.rules.careers.culture_weight_pct) if culture else values
    steered = steered_values(ctx.rules, steered, await open_wants(ctx.session, mortal.id))
    return career_move(ctx.rules, mortal.mortal_role, await role_levels(ctx.session, mortal.id, rows), steered)


async def left_to_beg(ctx: TickContext, mortal: EntityRow) -> bool:
    people = await people_of(ctx.session, mortal)
    if people is None:
        return False
    custom = await ctx.session.get(BodyCustomRow, people.id)
    if custom is not None and custom.pension:
        return False
    mercy = (await values_for(ctx.session, people.id)).get(ValueAxis.MERCY, 0)
    return mercy < ctx.rules.careers.beggar_mercy_below
