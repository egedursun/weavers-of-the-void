from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.tongues import DivineTongueRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.language_profile import has_script
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, has_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import set_stats
from aerona.language.titles import community_phrase
from aerona.language.vitality import VitalityChange, assess_vitality, death_notes_allowed, vitality_note


async def living_speakers(ctx: TickContext, language_id: int) -> int:
    native = [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.SPEAKS], targets=[language_id])]
    second = await ctx.session.scalars(
        select(SpeakerCohortRow.community_entity_id).where(
            SpeakerCohortRow.language_entity_id == language_id, SpeakerCohortRow.kind == SpeakerKind.SECOND, SpeakerCohortRow.share > 0
        )
    )
    living = [holder for holder in sorted({*native, *second}) if await living_entity(ctx.session, holder) is not None]
    return len(living)


async def kept_by_god(ctx: TickContext, language_id: int) -> bool:
    return await ctx.session.scalar(select(DivineTongueRow.god_node_id).where(DivineTongueRow.language_entity_id == language_id).limit(1)) is not None


async def last_home_phrase(ctx: TickContext, language_id: int) -> str | None:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(BondRow.target_node_id == language_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.PAST)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    home = await ctx.session.scalar(statement)
    return community_phrase(home.entity_type, home.name) if home is not None else None


async def liturgical(ctx: TickContext, language_id: int) -> bool:
    standing = await ctx.session.get(LanguageStandingRow, language_id)
    if standing is not None and standing.liturgical:
        return True
    used = await ctx.session.scalar(select(PeopleCultureRow.people_entity_id).where(PeopleCultureRow.liturgical_language_id == language_id).limit(1))
    return used is not None


@reads(
    "table.bonds",
    "table.divine_tongues",
    "table.entity_flags",
    "table.language_profiles",
    "table.language_standing",
    "table.language_standings",
    "table.people_culture",
    "table.speaker_cohorts",
)
@writes(
    "language.spread",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def language_death(ctx: TickContext) -> None:
    rules = ctx.rules
    notes_written = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        if await kept_by_god(ctx, language.id):
            continue
        dead = await has_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE)
        written = await has_script(ctx.session, language.id)
        assessment = assess_vitality(ctx.epoch - language.birth_epoch, await living_speakers(ctx, language.id), dead, written, rules)
        if assessment is None:
            continue
        if assessment.change is VitalityChange.DIED and await liturgical(ctx, language.id):
            await add_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE, ctx.epoch)
            ctx.count("kept_in_liturgy")
            text = f"No one is raised speaking {language.name} any more, yet the priests still chant in it."
            await note(ctx, text, key="languages.liturgical", ids=[language.id])
            continue
        if assessment.change is VitalityChange.DIED:
            await add_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE, ctx.epoch)
            await remove_flag(ctx.session, language.id, EntityFlag.REVIVED_LANGUAGE)
            if assessment.decipherable:
                await add_flag(ctx.session, language.id, EntityFlag.DECIPHERABLE, ctx.epoch)
            set_stats(language, spread=0)
            ctx.count("died")
            if death_notes_allowed(notes_written, rules):
                notes_written += 1
                await note(ctx, vitality_note(language.name, assessment, await last_home_phrase(ctx, language.id)), key="languages.died", ids=[language.id])
            continue
        await remove_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE)
        await remove_flag(ctx.session, language.id, EntityFlag.DECIPHERABLE)
        await add_flag(ctx.session, language.id, EntityFlag.REVIVED_LANGUAGE, ctx.epoch)
        ctx.count("revived")
        await note(ctx, vitality_note(language.name, assessment), key="languages.revived", ids=[language.id])


PHASES = (Phase("language_death", language_death),)
