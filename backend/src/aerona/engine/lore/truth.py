from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.theories import DOMAINS
from aerona.constants.units import PERCENT
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.society import KnowledgeBranch
from aerona.rules.registry import Rules

BRANCH_DOMAINS: dict[KnowledgeBranch, tuple[TheoryDomain, ...]] = {
    branch: tuple(domain for domain, spec in DOMAINS.items() if branch in spec.branches) for spec in DOMAINS.values() for branch in spec.branches
}
CONTRARY = frozenset({TheoryDomain.MEDICINE})


async def ruling(session: AsyncSession, holder_id: int, domain: TheoryDomain) -> TheoryProfileRow | None:
    return await session.scalar(
        select(TheoryProfileRow)
        .join(TheoryAdherentRow, TheoryAdherentRow.theory_entity_id == TheoryProfileRow.theory_entity_id)
        .where(TheoryAdherentRow.adherent_entity_id == holder_id, TheoryAdherentRow.orthodox.is_(True), TheoryProfileRow.domain == domain)
        .limit(1)
    )


def truth_factor(rules: Rules, correctness: int) -> float:
    return 1 + rules.theories.effect_pct * (correctness - PERCENT / 2) / (PERCENT / 2) / PERCENT


async def theory_factor(session: AsyncSession, rules: Rules, holder_id: int | None, domain: TheoryDomain) -> float:
    if holder_id is None:
        return 1.0
    row = await ruling(session, holder_id, domain)
    return truth_factor(rules, row.correctness) if row is not None else 1.0


async def branch_factor(session: AsyncSession, rules: Rules, holder_id: int, branch: KnowledgeBranch) -> float:
    factor = 1.0
    for domain in BRANCH_DOMAINS.get(branch, ()):
        factor *= await theory_factor(session, rules, holder_id, domain)
    return factor


async def ruling_truths(session: AsyncSession, domain: TheoryDomain) -> dict[int, int]:
    rows = await session.execute(
        select(TheoryAdherentRow.adherent_entity_id, TheoryProfileRow.correctness)
        .join(TheoryProfileRow, TheoryProfileRow.theory_entity_id == TheoryAdherentRow.theory_entity_id)
        .where(TheoryAdherentRow.orthodox.is_(True), TheoryProfileRow.domain == domain)
    )
    return dict(rows.all())
