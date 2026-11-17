from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.customs import BorderControlRow, MeasureStandardRow, MembershipCategoryRow, MembershipRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.customs import MemberRight
from aerona.domain.enums.mind import Profession
from aerona.engine.customs.grades import UNWED_GRADES, grade_of
from aerona.rules.registry import Rules

ARMED = frozenset({Profession.SOLDIER.value, Profession.COMMANDER.value, Profession.RIDER.value})


async def has_right(session: AsyncSession, mortal_id: int, right: MemberRight, polity_id: int | None = None) -> bool:
    member = await session.get(MembershipRow, mortal_id)
    if member is None or (polity_id is not None and member.polity_entity_id != polity_id):
        return True
    category = await session.get(MembershipCategoryRow, (member.polity_entity_id, member.category))
    return category is None or right.value in category.rights


async def unwed_by_law(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    return not await has_right(session, first.id, MemberRight.MARRIAGE) or not await has_right(session, second.id, MemberRight.MARRIAGE)


async def unarmed(session: AsyncSession, mortal_id: int) -> frozenset[str]:
    if await grade_of(session, mortal_id) in UNWED_GRADES:
        return ARMED
    return frozenset() if await has_right(session, mortal_id, MemberRight.ARMS) else ARMED


@memoized(PolityMemberRow)
async def realm_of(session: AsyncSession, town_id: int) -> int | None:
    found = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    return int(found) if found is not None else None


async def measured(session: AsyncSession, town_id: int) -> bool:
    realm = await realm_of(session, town_id)
    row = await session.get(MeasureStandardRow, realm) if realm is not None else None
    return row is not None and row.standard


async def crossing(session: AsyncSession, rules: Rules, ends: tuple[int, int]) -> tuple[float, float, int | None]:
    first, second = await realm_of(session, ends[0]), await realm_of(session, ends[1])
    factor = 1 + rules.measures.trade_pct / PERCENT if await measured(session, ends[0]) and await measured(session, ends[1]) else 1.0
    border = await session.get(BorderControlRow, second) if second is not None and second != first else None
    if border is None:
        return factor, 0.0, None
    factor *= max(0.0, 1 - border.delay * rules.borders.delay_pct / PERCENT * border.enforcement / PERCENT)
    fee = border.fee * rules.borders.fee_per_100 / PERCENT / PERCENT * (1 - border.corruption * rules.borders.forged_pass_pct / PERCENT / PERCENT)
    return factor, fee, second
