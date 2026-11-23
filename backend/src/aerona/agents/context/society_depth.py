from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, PolityLoyaltyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.society import SocialClass
from aerona.engine.demography.basket import held_got, needs_of, standing_of
from aerona.engine.demography.wealth import per_head


@dataclass(frozen=True)
class DepthLines:
    needs: list[str] = field(default_factory=list)
    wealth: str = ""
    loyalty: str = ""
    labour: list[str] = field(default_factory=list)


async def need_lines(session: AsyncSession, home: EntityRow, social: SocialClass | None) -> list[str]:
    if social is None:
        return []
    lines: list[str] = []
    for (social_class, commodity), row in sorted((await needs_of(session, home.id)).items(), key=lambda item: item[0][1].value):
        if social_class is not social or row.wanted <= 0:
            continue
        got = min(row.wanted, held_got(row.wanted, row.got, row.held_pct))
        if got < row.wanted:
            lines.append(f"{spoken(commodity)} {round(got * PERCENT / row.wanted)}% met")
    return lines


async def wealth_line(session: AsyncSession, home: EntityRow, social: SocialClass | None) -> str:
    society = await session.get(CommunitySocietyRow, home.id)
    if society is None:
        return ""
    standing = await standing_of(session, home.id)
    row = standing.get(social) if social is not None else None
    mine = f"your class holds {per_head(row, society.share(social))} wealth a head; " if row is not None and social is not None else ""
    return f"{mine}inequality (Gini) {society.gini} of 100"


async def loyalty_line(session: AsyncSession, home: EntityRow) -> str:
    row = await session.scalar(select(PolityLoyaltyRow).where(PolityLoyaltyRow.member_entity_id == home.id).limit(1))
    if row is None:
        return ""
    realm = await session.get(EntityRow, row.polity_entity_id)
    return (
        f"loyalty to {realm.name if realm is not None else 'the realm'} {row.loyalty} of 100 "
        f"(value distance {row.value_distance}, grievances {row.grievances}, benefits {row.benefits})"
    )


async def labour_lines(session: AsyncSession, home: EntityRow) -> list[str]:
    rows = list(await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == home.id, LabourRow.workers > 0)))
    lines = [
        f"{row.workers} at {spoken(row.job)}{' (held)' if row.held else ''}" for row in sorted(rows, key=lambda item: -item.workers) if row.job is not Job.IDLE
    ]
    corvee = await session.get(CorveeRow, home.id)
    if corvee is not None:
        lines.append(f"a corvee takes {corvee.share_pct}% of the workers for great works")
    return lines


async def depth_lines(session: AsyncSession, home: EntityRow, social: SocialClass | None) -> DepthLines:
    return DepthLines(
        needs=await need_lines(session, home, social),
        wealth=await wealth_line(session, home, social),
        loyalty=await loyalty_line(session, home),
        labour=await labour_lines(session, home),
    )
