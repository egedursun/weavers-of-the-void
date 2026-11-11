from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.tongues import LanguageStage
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import trade_links
from aerona.engine.lore.language import learn_second, tongues_of
from aerona.engine.notes import note
from aerona.engine.primitives.first_bonds import store_words
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.queries import connect, living_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.tongues.grammar import simplify
from aerona.language.lexicon import LexiconEntry

PIDGIN_SUBTYPE = "pidgin"
CREOLE_SUBTYPE = "creole"
PIDGIN_POWER = 1
PIDGIN_WORDS = 8
PIDGIN_SHARE = 20


@dataclass
class PidginTally:
    born: int = 0
    creolised: int = 0


async def words_from(ctx: TickContext, language: EntityRow, origin: str) -> list[LexiconEntry]:
    rows = list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id)))
    rng = ctx.rng(f"pidgin.words.{language.id}.{ctx.epoch}")
    rng.shuffle(rows)
    return [LexiconEntry(word=row.word, meaning=row.meaning, origin=origin) for row in rows[:PIDGIN_WORDS] if row.part_of_speech is not None]


async def already_talk(ctx: TickContext, first: int, second: int) -> bool:
    ours = await tongues_of(ctx.session, first)
    theirs = await tongues_of(ctx.session, second)
    for tongue in ours & theirs:
        profile = await ctx.session.get(LanguageProfileRow, tongue)
        if profile is not None and profile.stage is LanguageStage.PIDGIN:
            return True
    return bool(ours & theirs)


async def make_pidgin(ctx: TickContext, first: EntityRow, second: EntityRow) -> EntityRow | None:
    one, other = await spoken_language(ctx.session, first.id), await spoken_language(ctx.session, second.id)
    if one is None or other is None or one.id == other.id:
        return None
    pidgin = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=f"{first.name} Pidgin",
            body=f"A contact tongue that the traders of {first.name} and {second.name} made from {one.name} and {other.name}; no one is raised in it yet.",
            stats=LanguageStats(spread=0, complexity=0, sacredness=0),
            power=PIDGIN_POWER,
            world_id=first.world_id,
            subtype=PIDGIN_SUBTYPE,
        ),
    )
    profile = await language_profile(ctx.session, pidgin, one.id)
    profile.stage = LanguageStage.PIDGIN
    await simplify(ctx.session, ctx.rules, pidgin.id, ctx.epoch)
    for parent in (one, other):
        await connect(ctx.session, pidgin.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, description=PIDGIN_SUBTYPE)
        await store_words(ctx, pidgin, await words_from(ctx, parent, f"from {parent.name} (pidgin)"), first.id)
    for community in (first, second):
        await learn_second(ctx, community.id, pidgin.id, PIDGIN_SHARE)
    await note(
        ctx,
        f"The traders of {first.name} and {second.name}, who shared no tongue, made one between them: {pidgin.name}.",
        key="tongues.pidgin",
        ids=[first.id, second.id, pidgin.id],
        kind=ChronicleKind.LANGUAGE,
    )
    return pidgin


async def creolise(ctx: TickContext, pidgin: EntityRow, profile: LanguageProfileRow, tally: PidginTally) -> bool:
    table = ctx.rules.pidgins
    if ctx.epoch - pidgin.birth_epoch < table.creole_after:
        return False
    cohort = await ctx.session.scalar(
        select(SpeakerCohortRow)
        .where(SpeakerCohortRow.language_entity_id == pidgin.id, SpeakerCohortRow.kind == SpeakerKind.SECOND, SpeakerCohortRow.share >= table.native_share)
        .order_by(SpeakerCohortRow.share.desc(), SpeakerCohortRow.community_entity_id)
        .limit(1)
    )
    community = await living_entity(ctx.session, cohort.community_entity_id) if cohort is not None else None
    if community is None or held(community.id):
        return False
    profile.stage = LanguageStage.CREOLE
    pidgin.subtype = CREOLE_SUBTYPE
    await connect(ctx.session, community.id, pidgin.id, BondKind.SPEAKS, ctx.epoch, description=CREOLE_SUBTYPE)
    tally.creolised += 1
    await note(
        ctx,
        f"The children of {community.name} grew up speaking {pidgin.name}, and the contact tongue became a creole.",
        key="tongues.creolised",
        ids=[community.id, pidgin.id],
        kind=ChronicleKind.LANGUAGE,
    )
    return True


async def pidgin_world(ctx: TickContext, tally: PidginTally) -> None:
    table = ctx.rules.pidgins
    for link in sorted(await trade_links(ctx), key=lambda item: (-item.volume, item.first, item.second)):
        first, second = await living_entity(ctx.session, link.first), await living_entity(ctx.session, link.second)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if held(first.id, second.id) or await already_talk(ctx, first.id, second.id):
            continue
        if ctx.rng(f"pidgin.{first.id}.{second.id}.{ctx.epoch}").chance(table.contact_pct) and await make_pidgin(ctx, first, second) is not None:
            tally.born += 1
    for profile in list(await ctx.session.scalars(select(LanguageProfileRow).where(LanguageProfileRow.stage == LanguageStage.PIDGIN))):
        pidgin = await living_entity(ctx.session, profile.entity_id)
        if pidgin is not None and not held(pidgin.id):
            await creolise(ctx, pidgin, profile, tally)
    await ctx.session.flush()
