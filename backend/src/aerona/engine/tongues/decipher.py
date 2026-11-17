from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sites import ExcavationRow, ExcavationStageRow
from aerona.db.tables.tongues import DecipherWorkRow
from aerona.db.write_guard import held
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.site import ExcavationFind
from aerona.domain.models.entity_stats import TheoryStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import has_flag, remove_flag
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record as record_incident

THEORY_POWER = 2
MISREAD_CORRECTNESS = 10


@dataclass
class DecipherTally:
    progressed: int = 0
    deciphered: int = 0
    misread: int = 0
    bilingual: int = 0


async def corpus_of(ctx: TickContext, language_id: int) -> int:
    total = await ctx.session.scalar(select(func.coalesce(func.sum(ArtworkProfileRow.copies), 0)).where(ArtworkProfileRow.language_entity_id == language_id))
    return int(total or 0)


async def relatives(ctx: TickContext, language: EntityRow) -> int:
    profile = await ctx.session.get(LanguageProfileRow, language.id)
    parent = profile.parent_language_id if profile is not None else None
    kin = select(LanguageProfileRow.entity_id).where(
        (LanguageProfileRow.parent_language_id == language.id)
        | ((LanguageProfileRow.parent_language_id == parent) if parent is not None else (LanguageProfileRow.entity_id == -1))
    )
    rows = await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(kin), EntityRow.id != language.id, EntityRow.status == EntityStatus.CANON))
    living = [row for row in rows if not await has_flag(ctx.session, row.id, EntityFlag.DEAD_LANGUAGE)]
    return len(living)


async def best_scholar(ctx: TickContext, language: EntityRow, work: DecipherWorkRow) -> EntityRow | None:
    if work.scholar_entity_id is not None:
        chosen = await ctx.session.get(EntityRow, work.scholar_entity_id)
        if chosen is not None and chosen.status is EntityStatus.CANON:
            return chosen
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            SkillRow.skill == SkillKind.LANGUAGES,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == language.world_id,
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
        .limit(1)
    )
    return found


async def skill_in(ctx: TickContext, scholar_id: int, language_id: int | None = None) -> SkillRow | None:
    subject = SkillRow.subject_node_id == language_id if language_id is not None else SkillRow.subject_node_id.is_(None)
    found: SkillRow | None = await ctx.session.scalar(
        select(SkillRow).where(SkillRow.holder_node_id == scholar_id, SkillRow.skill == SkillKind.LANGUAGES, subject).limit(1)
    )
    return found


async def learn(ctx: TickContext, scholar: EntityRow, language_id: int, level: int) -> None:
    found = await skill_in(ctx, scholar.id, language_id)
    if found is None:
        ctx.session.add(
            SkillRow(
                holder_node_id=scholar.id,
                skill=SkillKind.LANGUAGES,
                subject_node_id=language_id,
                level=level,
                peak=level,
                last_used_epoch=ctx.epoch,
                source=SkillSource.PRACTICE,
            )
        )
    else:
        found.level, found.peak, found.last_used_epoch = max(found.level, level), max(found.peak, level), ctx.epoch


async def work_on(ctx: TickContext, language: EntityRow) -> DecipherWorkRow:
    row = await ctx.session.get(DecipherWorkRow, language.id)
    if row is None:
        row = DecipherWorkRow(language_entity_id=language.id, progress=0, corpus=0, bilingual=False, errors=0, started_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def misreading(ctx: TickContext, language: EntityRow, work: DecipherWorkRow, scholar: EntityRow) -> EntityRow:
    theory = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.THEORY,
            name=f"The reading of {language.name} by {scholar.name}",
            body=f"A reading of {language.name} that {scholar.name} set down while the script was only half understood.",
            stats=TheoryStats(),
            power=THEORY_POWER,
            world_id=language.world_id,
            pending=False,
        ),
    )
    ctx.session.add(
        TheoryProfileRow(
            theory_entity_id=theory.id,
            domain=TheoryDomain.HISTORY,
            claim=f"what the {language.name} texts say, as {scholar.name} read them",
            correctness=MISREAD_CORRECTNESS,
            founder_entity_id=scholar.id,
            locked=[],
        )
    )
    await record_incident(
        ctx,
        "tongues.misread",
        roles={IncidentRole.ACTOR: scholar.id, IncidentRole.SUBJECT: language.id, IncidentRole.PRODUCT: theory.id},
        facts={"errors": work.errors},
    )
    return theory


async def bilingual_finds(ctx: TickContext, tally: DecipherTally) -> None:
    table = ctx.rules.decipherment
    found = await ctx.session.execute(
        select(ExcavationStageRow.id, EntityRow.world_id)
        .join(ExcavationRow, ExcavationRow.id == ExcavationStageRow.excavation_id)
        .join(EntityRow, EntityRow.id == ExcavationRow.site_entity_id)
        .where(ExcavationStageRow.find == ExcavationFind.BOOK, ExcavationStageRow.resolved_epoch == ctx.epoch)
    )
    for stage_id, world_id in found:
        works = await ctx.session.scalars(
            select(DecipherWorkRow)
            .join(EntityRow, EntityRow.id == DecipherWorkRow.language_entity_id)
            .where(EntityRow.world_id == world_id, DecipherWorkRow.bilingual.is_(False), DecipherWorkRow.progress < PERCENT)
            .order_by(DecipherWorkRow.language_entity_id)
        )
        work = next(iter(works), None)
        if work is not None and "bilingual" not in work.locked and ctx.rng(f"decipher.bilingual.{stage_id}").chance(table.bilingual_find_pct):
            work.bilingual = True
            tally.bilingual += 1


async def study(ctx: TickContext, language: EntityRow, scholar: EntityRow, tally: DecipherTally) -> DecipherWorkRow:
    table = ctx.rules.decipherment
    work = await work_on(ctx, language)
    if "corpus" not in work.locked:
        work.corpus = await corpus_of(ctx, language.id)
    if "scholar_entity_id" not in work.locked:
        work.scholar_entity_id = scholar.id
    general = await skill_in(ctx, scholar.id)
    gain = table.base + round_half_up((general.level if general is not None else 0) * table.skill_pct / PERCENT)
    gain += work.corpus // table.corpus_step + (table.bilingual if work.bilingual else 0) + table.cognate * await relatives(ctx, language)
    if "progress" not in work.locked:
        work.progress = clamp_int(work.progress + gain, 0, PERCENT)
    work.updated_epoch = ctx.epoch
    tally.progressed += 1
    await learn(ctx, scholar, language.id, work.progress // 2)
    if work.progress < PERCENT and "errors" not in work.locked and ctx.rng(f"decipher.error.{language.id}.{ctx.epoch}").chance(table.error_pct):
        work.errors += 1
        tally.misread += 1
        if work.errors == table.legend_errors:
            await misreading(ctx, language, work, scholar)
    if work.progress >= PERCENT and await has_flag(ctx.session, language.id, EntityFlag.DECIPHERABLE):
        await remove_flag(ctx.session, language.id, EntityFlag.DECIPHERABLE)
        await learn(ctx, scholar, language.id, PERCENT // 2)
        tally.deciphered += 1
        await record_incident(
            ctx, "tongues.deciphered", roles={IncidentRole.ACTOR: scholar.id, IncidentRole.SUBJECT: language.id}, facts={"errors": work.errors}
        )
    return work


async def decipher_world(ctx: TickContext, tally: DecipherTally) -> None:
    await bilingual_finds(ctx, tally)
    for language in await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE).order_by(EntityRow.id)):
        if held(language.id) or not await has_flag(ctx.session, language.id, EntityFlag.DECIPHERABLE):
            continue
        work = await work_on(ctx, language)
        scholar = await best_scholar(ctx, language, work)
        if scholar is not None and not held(scholar.id):
            await study(ctx, language, scholar, tally)
    await ctx.session.flush()
