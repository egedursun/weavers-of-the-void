from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import KNOWLEDGE_BRANCH_TRAITS, having
from aerona.catalog.tongues import BASES
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.domain.enums.crafts import Notation
from aerona.domain.enums.life_traits import KnowledgeBranchTrait
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.tongues import NumeralBase
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.queries import spoken_language
from aerona.rules.registry import Rules

RECKONED = having(KNOWLEDGE_BRANCH_TRAITS, KnowledgeBranchTrait.RECKONED)


async def system_of(session: AsyncSession, holder_id: int | None) -> NumberSystemRow | None:
    holder = await session.get(EntityRow, holder_id) if holder_id is not None else None
    people = await people_of(session, holder) if holder is not None else None
    return await session.get(NumberSystemRow, people.id) if people is not None else None


async def counting_of(session: AsyncSession, holder_id: int | None) -> tuple[NumeralBase, bool]:
    holder = await session.get(EntityRow, holder_id) if holder_id is not None else None
    people = await people_of(session, holder) if holder is not None else None
    tongue = None
    for speaker in (holder, people):
        if tongue is None and speaker is not None:
            tongue = await spoken_language(session, speaker.id)
    profile = await session.get(LanguageProfileRow, tongue.id) if tongue is not None else None
    if profile is None:
        return NumeralBase.DECIMAL, True
    return profile.numeral_base, profile.writing_system is not None


async def base_factor(session: AsyncSession, rules: Rules, holder_id: int | None) -> float:
    base, written = await counting_of(session, holder_id)
    spec = BASES[base]
    if spec.needs_writing and written:
        return 1.0
    return int(getattr(rules.tongues, spec.rule)) / PERCENT


async def fine_division(session: AsyncSession, rules: Rules, holder_id: int | None) -> float:
    base, _ = await counting_of(session, holder_id)
    return 1 + rules.tongues.fine_division_pct / PERCENT if BASES[base].fine_division else 1.0


async def numeracy_of(session: AsyncSession, rules: Rules, holder_id: int | None) -> int:
    row = await system_of(session, holder_id)
    if row is None:
        return 0
    return min(PERCENT, round(row.numeracy * await base_factor(session, rules, holder_id)))


async def reckoned(session: AsyncSession, rules: Rules, holder_id: int | None, pct: int) -> float:
    return 1 + await numeracy_of(session, rules, holder_id) * pct / PERCENT / PERCENT


async def notation_boost(session: AsyncSession, rules: Rules, community_id: int, branch: KnowledgeBranch) -> float:
    if branch not in RECKONED:
        return 1.0
    row = await system_of(session, community_id)
    if row is None:
        return 1.0
    steps = int(row.zero) + int(row.notation is Notation.POSITIONAL)
    sky = await fine_division(session, rules, community_id) if branch is KnowledgeBranch.ASTRONOMY else 1.0
    return (1 + steps * rules.numeracy.research_pct / PERCENT) * sky * await base_factor(session, rules, community_id)


async def price_gaps(session: AsyncSession, rules: Rules, ends: tuple[int, int]) -> dict[int, float]:
    return {end: 1 - await numeracy_of(session, rules, end) * rules.numeracy.trade_pct / PERCENT / PERCENT for end in ends}
