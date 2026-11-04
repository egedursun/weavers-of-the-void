from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow, LanguageIntelligibilityRow, LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

SAME = 100
KIN_STEP = 20
KIN_BASE = 80
SACRED_STAT = 60


async def lineage(session: AsyncSession, language_id: int) -> list[int]:
    chain = [language_id]
    seen = {language_id}
    current = language_id
    while True:
        profile = await session.get(LanguageProfileRow, current)
        parent = profile.parent_language_id if profile is not None else None
        if parent is None or parent in seen:
            return chain
        chain.append(parent)
        seen.add(parent)
        current = parent


async def lexicon_overlap(session: AsyncSession, first: int, second: int) -> float:
    words = select(LexemeRow.meaning).where(LexemeRow.language_entity_id == first)
    shared = await session.scalar(
        select(func.count(func.distinct(LexemeRow.meaning))).where(LexemeRow.language_entity_id == second, LexemeRow.meaning.in_(words))
    )
    total = await session.scalar(select(func.count(func.distinct(LexemeRow.meaning))).where(LexemeRow.language_entity_id.in_([first, second])))
    shared_forms = await session.scalar(
        select(func.count(LexemeRow.id)).where(
            LexemeRow.language_entity_id == second,
            LexemeRow.word.in_(select(LexemeRow.word).where(LexemeRow.language_entity_id == first)),
        )
    )
    if not total:
        return 0.0
    return min(1.0, (int(shared_forms or 0) + int(shared or 0) / 4) / max(1, int(total)))


async def compute(session: AsyncSession, rules: Rules, first: int, second: int) -> int:
    if first == second:
        return SAME
    one, other = await lineage(session, first), await lineage(session, second)
    common = next((index for index, item in enumerate(one) if item in other), None)
    kinship = 0
    if common is not None:
        steps = common + other.index(one[common])
        kinship = max(0, KIN_BASE - steps * KIN_STEP)
    words = round_half_up(await lexicon_overlap(session, first, second) * PERCENT * rules.interpreters.shared_lexicon_pct / PERCENT)
    return clamp_int(max(kinship, words), 0, PERCENT)


async def intelligibility(session: AsyncSession, rules: Rules, first: int | None, second: int | None, epoch: int) -> int:
    if first is None or second is None:
        return SAME
    if first == second:
        return SAME
    low, high = sorted((first, second))
    row = await session.get(LanguageIntelligibilityRow, (low, high))
    if row is None:
        row = LanguageIntelligibilityRow(first_entity_id=low, second_entity_id=high, value=await compute(session, rules, low, high), epoch=epoch)
        session.add(row)
    return row.value


async def interpreter(session: AsyncSession, rules: Rules, *communities: int, tongues: set[int] | None = None) -> bool:
    mortals = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(communities)
    )
    subject = SkillRow.subject_node_id.is_(None) if not tongues else (SkillRow.subject_node_id.is_(None) | SkillRow.subject_node_id.in_(list(tongues)))
    found = await session.scalar(
        select(SkillRow.holder_node_id)
        .where(SkillRow.skill == SkillKind.LANGUAGES, SkillRow.level >= rules.interpreters.interpreter_skill, SkillRow.holder_node_id.in_(mortals), subject)
        .limit(1)
    )
    return found is not None


async def tongues_of(session: AsyncSession, community_id: int) -> set[int]:
    native = await spoken_language(session, community_id)
    found = {native.id} if native is not None else set()
    seconds = await session.scalars(
        select(SpeakerCohortRow.language_entity_id).where(SpeakerCohortRow.community_entity_id == community_id, SpeakerCohortRow.share > 0)
    )
    found.update(seconds)
    return found


async def barrier(session: AsyncSession, rules: Rules, first: int, second: int, epoch: int) -> float:
    ours, theirs = await tongues_of(session, first), await tongues_of(session, second)
    if not ours or not theirs or ours & theirs:
        return 1.0
    best = max([await intelligibility(session, rules, one, other, epoch) for one in ours for other in theirs] or [SAME])
    if best >= SAME:
        return 1.0
    if await interpreter(session, rules, first, second, tongues=ours | theirs):
        return 1.0
    floor = rules.interpreters.barrier_floor_pct / PERCENT
    return floor + (1 - floor) * best / PERCENT


async def standing_of(session: AsyncSession, language: EntityRow, epoch: int) -> LanguageStandingRow:
    row = await session.get(LanguageStandingRow, language.id)
    if row is None:
        row = LanguageStandingRow(
            language_entity_id=language.id,
            prestige=30,
            standardisation=0,
            liturgical=False,
            lingua_franca=False,
            prestige_parts={},
            updated_epoch=epoch,
            locked=[],
        )
        session.add(row)
    return row


async def speakers(session: AsyncSession, language_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == language_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    return list(await session.scalars(statement))


async def prestige_parts(ctx: TickContext, language: EntityRow) -> dict[str, int]:
    table = ctx.rules.prestige
    voices = await speakers(ctx.session, language.id)
    realms = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(voices))
    power = await ctx.session.scalar(select(func.coalesce(func.max(PolityProfileRow.tier), 0)).where(PolityProfileRow.polity_entity_id.in_(realms)))
    works = await ctx.session.scalar(select(func.count(ArtworkProfileRow.artwork_entity_id)).where(ArtworkProfileRow.language_entity_id == language.id))
    parts = {
        "the power of its speakers": round_half_up(int(power or 0) * 10 * table.power_pct / PERCENT),
        "its literature": min(PERCENT // 2, int(works or 0) * table.literature),
    }
    if (stat(language, "sacredness") or 0) >= SACRED_STAT:
        parts["its holiness"] = table.sacred
    return parts


SCRIPT_KEYS = {
    WritingSystem.ALPHABET: "alphabet_pct",
    WritingSystem.SYLLABARY: "syllabary_pct",
    WritingSystem.PICTOGRAPHIC: "logographic_pct",
    WritingSystem.KNOT: "knots_pct",
    WritingSystem.NOTCH: "knots_pct",
}


async def script_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    language = await spoken_language(session, community_id)
    profile = await session.get(LanguageProfileRow, language.id) if language is not None else None
    if profile is None or profile.writing_system is None:
        return 1.0
    return int(getattr(rules.script, SCRIPT_KEYS[profile.writing_system])) / PERCENT


async def learn_second(ctx: TickContext, community_id: int, language_id: int, gain: int) -> int:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, SpeakerKind.SECOND))
    if row is None:
        row = SpeakerCohortRow(community_entity_id=community_id, language_entity_id=language_id, kind=SpeakerKind.SECOND, share=0, since_epoch=ctx.epoch)
        ctx.session.add(row)
    row.share = clamp_int(row.share + gain, 0, PERCENT)
    return row.share
