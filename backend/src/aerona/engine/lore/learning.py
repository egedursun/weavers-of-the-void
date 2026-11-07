from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import BRANCH_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import InstitutionRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.rules.registry import Rules

OFFICE_LEARNING = (*BRANCH_SKILLS[KnowledgeBranch.CIVICS], *BRANCH_SKILLS[KnowledgeBranch.WRITING], *BRANCH_SKILLS[KnowledgeBranch.ASTRONOMY])


async def realm_of(session: AsyncSession, community_id: int) -> int | None:
    return await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))


async def institution_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    table = rules.research_depth
    rows = list(await session.scalars(select(InstitutionRow).where(InstitutionRow.community_entity_id == community_id)))
    embraced = sum(1 for row in rows if row.embraced)
    refusal = min(table.refusal_cap, sum(row.refused_epochs for row in rows if not row.embraced) * table.refusal_pct)
    return (1 + embraced * table.embrace_pct / PERCENT) * (1 - refusal / PERCENT)


async def court_scholar(session: AsyncSession, polity_id: int) -> OfficeRow | None:
    return await session.scalar(
        select(OfficeRow)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.COURT_SCHOLAR, OfficeRow.holder_entity_id.is_not(None))
        .limit(1)
    )


async def patron_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    realm = await realm_of(session, community_id)
    office = await court_scholar(session, realm) if realm is not None else None
    if office is None or office.holder_entity_id is None:
        return 1.0
    learning = list(OFFICE_LEARNING)
    skill = await session.scalar(select(func.max(SkillRow.level)).where(SkillRow.holder_node_id == office.holder_entity_id, SkillRow.skill.in_(learning)))
    return 1 + rules.research_depth.patron_research_pct * int(skill or 0) / PERCENT / PERCENT
