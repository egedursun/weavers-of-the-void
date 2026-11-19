from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_shapes import CALLED_PROFESSIONS
from aerona.catalog.mind import BRANCH_SKILLS, PROFESSIONS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import BookContentRow, RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import Profession, SkillKind, SkillSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.customs.rights import unarmed
from aerona.engine.folkways.purity import barred_professions
from aerona.engine.means.media import legible
from aerona.engine.mind.book import is_locked, mind_of, set_skill, skills_of
from aerona.engine.mind.skills import SKILL_LOCK, level_cost, practise
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

LECTURE_HALLS = frozenset({EngineKind.SCHOOL, EngineKind.LIBRARY})


async def subject_skill(session: AsyncSession, holder_id: int, skill: SkillKind, subject_id: int) -> SkillRow | None:
    found: SkillRow | None = await session.scalar(
        select(SkillRow).where(SkillRow.holder_node_id == holder_id, SkillRow.skill == skill, SkillRow.subject_node_id == subject_id).limit(1)
    )
    return found


async def practise_subject(session: AsyncSession, rules: Rules, holder_id: int, skill: SkillKind, *, subject_id: int, xp: float, epoch: int) -> int:
    if xp <= 0 or is_locked(await mind_of(session, holder_id), SKILL_LOCK):
        return 0
    row = await subject_skill(session, holder_id, skill, subject_id)
    if row is None:
        row = await set_skill(session, holder_id, skill, 0, epoch=epoch, source=SkillSource.PRACTICE, subject_node_id=subject_id)
    row.xp += round(xp)
    gained = 0
    while row.level < PERCENT and row.xp >= level_cost(rules, row.level):
        row.xp -= level_cost(rules, row.level)
        row.level += 1
        gained += 1
    row.peak = max(row.peak, row.level)
    row.last_used_epoch = epoch
    await session.flush()
    return gained


async def tongue_level(session: AsyncSession, holder_id: int, language_id: int) -> int:
    row = await subject_skill(session, holder_id, SkillKind.LANGUAGES, language_id)
    return row.level if row is not None else 0


async def speak_tongues(ctx: TickContext, mortal: EntityRow) -> int:
    gained = 0
    for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[mortal.id]):
        gained += await practise_subject(
            ctx.session, ctx.rules, mortal.id, SkillKind.LANGUAGES, subject_id=bond.target_node_id, xp=ctx.rules.skills.speak_xp, epoch=ctx.epoch
        )
    return gained


async def school_level(session: AsyncSession, caster_id: int, rite_id: int) -> int:
    rite = await session.get(RiteProfileRow, rite_id)
    if rite is None:
        return 0
    same_school = select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.school == rite.school)
    found = await session.scalar(
        select(SkillRow.level)
        .where(SkillRow.holder_node_id == caster_id, SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id.in_(same_school))
        .order_by(SkillRow.level.desc())
        .limit(1)
    )
    return int(found or 0)


def best_profession(rules: Rules, rows: dict[SkillKind, SkillRow], barred: frozenset[str] = frozenset()) -> Profession | None:
    scored = {
        profession: max((rows[skill].level for skill in spec.skills if skill in rows), default=0)
        for profession, spec in PROFESSIONS.items()
        if profession.value not in barred
    }
    if not scored:
        return None
    best = max(scored, key=lambda profession: (scored[profession], profession.value))
    return best if scored[best] >= rules.skills.profession_level else None


async def refresh_profession(session: AsyncSession, rules: Rules, mortal: EntityRow, profile: MortalProfileRow) -> Profession | None:
    if not is_held(profile, "profession"):
        barred = await barred_professions(session, mortal.id) | await unarmed(session, mortal.id)
        best = best_profession(rules, await skills_of(session, mortal.id), barred)
        current = profile.profession
        called = current is not None and current in CALLED_PROFESSIONS and current.value not in barred
        profile.profession = current if best is None and called else best
    return profile.profession


async def masters_of(ctx: TickContext, community_id: int, skills: tuple[SkillKind, ...], *, exclude: int) -> list[SkillRow]:
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, [community_id]),
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.id != exclude,
    )
    rows = await ctx.session.scalars(
        select(SkillRow)
        .where(
            SkillRow.holder_node_id.in_(mortals),
            SkillRow.skill.in_(list(skills)),
            SkillRow.subject_node_id.is_(None),
            SkillRow.level >= ctx.rules.skills.master_level,
        )
        .order_by(SkillRow.level.desc(), SkillRow.id)
    )
    return list(rows)


async def watch_masters(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> int:
    if profile.profession is None or mortal.location_id is None:
        return 0
    skills = PROFESSIONS[profile.profession].skills
    found = await masters_of(ctx, mortal.location_id, skills, exclude=mortal.id)
    if not found:
        return 0
    master = found[0]
    own = (await skills_of(ctx.session, mortal.id)).get(master.skill)
    if own is not None and own.level >= master.level:
        return 0
    xp = ctx.rules.skills.demonstration_xp * master.level / PERCENT
    return await practise(ctx.session, ctx.rules, mortal.id, master.skill, xp, epoch=ctx.epoch, source=SkillSource.TEACHING)


async def lecture_hall(ctx: TickContext, community_id: int) -> bool:
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.location_id == community_id,
            EntityRow.entity_type == EntityType.STRUCTURE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.engine_kind.in_(list(LECTURE_HALLS)),
        )
        .limit(1)
    )
    return found is not None


async def attend_lectures(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> int:
    if profile.profession is None or mortal.location_id is None or not await lecture_hall(ctx, mortal.location_id):
        return 0
    found = await masters_of(ctx, mortal.location_id, PROFESSIONS[profile.profession].skills, exclude=mortal.id)
    lecturers = [row for row in found if (await skills_of(ctx.session, row.holder_node_id)).get(SkillKind.TEACHING) is not None]
    if not lecturers:
        return 0
    lecturer = lecturers[0]
    gained = await practise(ctx.session, ctx.rules, mortal.id, lecturer.skill, ctx.rules.skills.lecture_xp, epoch=ctx.epoch, source=SkillSource.TEACHING)
    await practise(ctx.session, ctx.rules, lecturer.holder_node_id, SkillKind.TEACHING, ctx.rules.skills.lecture_xp / 2, epoch=ctx.epoch)
    return gained


async def read_books(ctx: TickContext, mortal: EntityRow) -> int:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    rows = await ctx.session.execute(
        select(BookContentRow.book_entity_id, BookContentRow.fidelity, EntityRow.knowledge_branch)
        .join(EntityRow, EntityRow.id == BookContentRow.knowledge_entity_id)
        .where(BookContentRow.book_entity_id.in_(owned))
    )
    gained = 0
    for book, fidelity, branch in rows:
        skill = BRANCH_SKILLS.get(KnowledgeBranch(branch)) if branch is not None else None
        if skill is None:
            continue
        xp = ctx.rules.skills.book_xp * fidelity / PERCENT * await legible(ctx, book)
        gained += await practise(ctx.session, ctx.rules, mortal.id, skill, xp, epoch=ctx.epoch)
    return gained


async def learn(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> int:
    await refresh_profession(ctx.session, ctx.rules, mortal, profile)
    gained = await speak_tongues(ctx, mortal)
    gained += await watch_masters(ctx, mortal, profile)
    gained += await attend_lectures(ctx, mortal, profile)
    gained += await read_books(ctx, mortal)
    return gained
