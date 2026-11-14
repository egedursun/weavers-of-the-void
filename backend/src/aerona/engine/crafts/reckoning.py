from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.crafts import Notation
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.rules.registry import Rules

RECKONED = frozenset({KnowledgeBranch.ASTRONOMY, KnowledgeBranch.ARCHITECTURE, KnowledgeBranch.TRADE, KnowledgeBranch.SEAFARING})


async def system_of(session: AsyncSession, holder_id: int | None) -> NumberSystemRow | None:
    holder = await session.get(EntityRow, holder_id) if holder_id is not None else None
    people = await people_of(session, holder) if holder is not None else None
    return await session.get(NumberSystemRow, people.id) if people is not None else None


async def numeracy_of(session: AsyncSession, holder_id: int | None) -> int:
    row = await system_of(session, holder_id)
    return row.numeracy if row is not None else 0


async def reckoned(session: AsyncSession, holder_id: int | None, pct: int) -> float:
    return 1 + await numeracy_of(session, holder_id) * pct / PERCENT / PERCENT


async def notation_boost(session: AsyncSession, rules: Rules, community_id: int, branch: KnowledgeBranch) -> float:
    if branch not in RECKONED:
        return 1.0
    row = await system_of(session, community_id)
    if row is None:
        return 1.0
    steps = int(row.zero) + int(row.notation is Notation.POSITIONAL)
    return 1 + steps * rules.numeracy.research_pct / PERCENT


async def price_gaps(session: AsyncSession, rules: Rules, ends: tuple[int, int]) -> dict[int, float]:
    return {end: 1 - await numeracy_of(session, end) * rules.numeracy.trade_pct / PERCENT / PERCENT for end in ends}
