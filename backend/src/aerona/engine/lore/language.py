from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow, LanguageIntelligibilityRow, LanguageRegisterRow, LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import LanguageRegister, SpeakerKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.engine.body.customs import people_of
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
    heard = max(kinship, words)
    if heard <= 0:
        return 0
    sounds = round_half_up(await phonology_similarity(session, first, second) * rules.interpreters.phonology_pct)
    return clamp_int(heard + sounds, 0, PERCENT)


def overlap(first: tuple[str, ...], second: tuple[str, ...]) -> float:
    one, other = {item.casefold() for item in first}, {item.casefold() for item in second}
    union = one | other
    return len(one & other) / len(union) if union else 0.0


async def phonology_similarity(session: AsyncSession, first: int, second: int) -> float:
    one, other = await session.get(LanguageProfileRow, first), await session.get(LanguageProfileRow, second)
    if one is None or other is None:
        return 0.0
    a, b = one.phonology, other.phonology
    parts = (overlap(a.vowels, b.vowels), overlap(a.consonants, b.consonants), overlap(a.syllable_patterns, b.syllable_patterns))
    return sum(parts) / len(parts)


async def intelligibility(session: AsyncSession, rules: Rules, first: int | None, second: int | None, epoch: int) -> int:
    if first is None or second is None:
        return SAME
    if first == second:
        return SAME
    low, high = sorted((first, second))
    row = await session.get(LanguageIntelligibilityRow, (low, high))
    if row is None:
        row = LanguageIntelligibilityRow(first_entity_id=low, second_entity_id=high, value=await compute(session, rules, low, high), epoch=epoch, locked=[])
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
    return set(await known_tongues(session, community_id))


@memoized(BondRow, EntityRow, SpeakerCohortRow)
async def known_tongues(session: AsyncSession, community_id: int) -> frozenset[int]:
    native = await spoken_language(session, community_id)
    found = {native.id} if native is not None else set()
    seconds = await session.scalars(
        select(SpeakerCohortRow.language_entity_id).where(SpeakerCohortRow.community_entity_id == community_id, SpeakerCohortRow.share > 0)
    )
    found.update(seconds)
    return frozenset(found)


async def barrier(session: AsyncSession, rules: Rules, first: int, second: int, epoch: int) -> float:
    return await understood(session, rules, (first, second), (await tongues_of(session, first), await tongues_of(session, second)), epoch)


async def chosen_trade_tongue(session: AsyncSession, community_id: int) -> int | None:
    entity = await session.get(EntityRow, community_id)
    people = await people_of(session, entity) if entity is not None else None
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.trade_language_id if culture is not None else None


async def register_tongues(session: AsyncSession, holder_id: int, register: LanguageRegister) -> set[int]:
    row = await session.get(LanguageRegisterRow, (holder_id, register))
    if row is not None:
        return {row.language_entity_id}
    return await tongues_of(session, holder_id)


async def register_barrier(
    session: AsyncSession, rules: Rules, first: int, second: int, epoch: int, *, ours: LanguageRegister, theirs: LanguageRegister = LanguageRegister.COMMON
) -> float:
    one = await register_tongues(session, first, ours)
    other = await register_tongues(session, second, theirs)
    return await understood(session, rules, (first, second), (one, other), epoch)


async def understood(session: AsyncSession, rules: Rules, pair: tuple[int, int], tongues: tuple[set[int], set[int]], epoch: int) -> float:
    first, second = pair
    ours, theirs = tongues
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
    if language is None:
        return 1.0
    standard = 1 + await standardisation_of(session, language.id) * rules.prestige.standard_literacy_pct / (PERCENT * PERCENT)
    if profile is None or profile.writing_system is None:
        return standard
    return int(getattr(rules.script, SCRIPT_KEYS[profile.writing_system])) / PERCENT * standard


async def standardisation_of(session: AsyncSession, language_id: int | None) -> int:
    row = await session.get(LanguageStandingRow, language_id) if language_id is not None else None
    return row.standardisation if row is not None else 0


async def learn_second(ctx: TickContext, community_id: int, language_id: int, gain: int) -> int:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, SpeakerKind.SECOND))
    if held(community_id, language_id):
        return row.share if row is not None else 0
    if row is None:
        row = SpeakerCohortRow(
            community_entity_id=community_id, language_entity_id=language_id, kind=SpeakerKind.SECOND, share=0, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    if "share" not in (row.locked or []):
        row.share = clamp_int(row.share + gain, 0, PERCENT)
    return row.share


async def remeasure(ctx: TickContext) -> int:
    every = ctx.rules.interpreters.remeasure_epochs
    if every <= 0 or ctx.epoch % every:
        return 0
    measured = 0
    for row in list(await ctx.session.scalars(select(LanguageIntelligibilityRow).order_by(LanguageIntelligibilityRow.first_entity_id))):
        if "value" in (row.locked or []):
            continue
        row.value, row.epoch = await compute(ctx.session, ctx.rules, row.first_entity_id, row.second_entity_id), ctx.epoch
        measured += 1
    return measured


async def hold_register(ctx: TickContext, holder_id: int, register: LanguageRegister, language_id: int | None) -> bool:
    if language_id is None or held(holder_id, language_id):
        return False
    row = await ctx.session.get(LanguageRegisterRow, (holder_id, register))
    if row is None:
        ctx.session.add(LanguageRegisterRow(holder_entity_id=holder_id, register=register, language_entity_id=language_id, since_epoch=ctx.epoch, locked=[]))
        return True
    if "language_entity_id" in row.locked or row.language_entity_id == language_id:
        return False
    row.language_entity_id, row.since_epoch = language_id, ctx.epoch
    return True


async def traders(session: AsyncSession) -> set[int]:
    roads = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE)
    )
    return {end for pair in roads.all() for end in pair}


async def derive_registers(ctx: TickContext, courts: dict[int, int | None], liturgies: dict[int, int | None], franca: int | None) -> int:
    changed = 0
    for holder_id, language_id in sorted(courts.items()):
        changed += int(await hold_register(ctx, holder_id, LanguageRegister.COURT, language_id))
    for holder_id, language_id in sorted(liturgies.items()):
        changed += int(await hold_register(ctx, holder_id, LanguageRegister.LITURGICAL, language_id))
    speech = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    )
    common: dict[int, int] = {}
    for community_id, language_id in speech.all():
        common.setdefault(community_id, language_id)
    trading = await traders(ctx.session)
    for community_id, language_id in sorted(common.items()):
        changed += int(await hold_register(ctx, community_id, LanguageRegister.COMMON, language_id))
        if community_id in trading:
            chosen = await chosen_trade_tongue(ctx.session, community_id)
            trade = chosen if chosen is not None else franca if franca is not None and franca in await tongues_of(ctx.session, community_id) else language_id
            changed += int(await hold_register(ctx, community_id, LanguageRegister.TRADE, trade))
    return changed
