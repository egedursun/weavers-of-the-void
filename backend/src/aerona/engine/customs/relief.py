from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.customs import CommuteRow, CooperativeRow, PoorReliefRow, TavernRow, WelfareRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.customs import CoopPurpose
from aerona.rules.registry import Rules

TEN = 10
RELIEVING = frozenset({CoopPurpose.INSURANCE, CoopPurpose.BURIAL, CoopPurpose.CREDIT})


async def houses_in(session: AsyncSession, town_id: int) -> int:
    hosted = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.host_entity_id == town_id)
    return int(await session.scalar(select(func.count()).select_from(WelfareRow).where(WelfareRow.structure_entity_id.in_(hosted))) or 0)


async def realm_relief(session: AsyncSession, rules: Rules, town_id: int) -> int:
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    row = await session.get(PoorReliefRow, realm) if realm is not None else None
    return row.budget * rules.poor_relief.relief_per_coin * row.reach // TEN // PERCENT if row is not None else 0


async def poverty_relief(session: AsyncSession, rules: Rules, town_id: int) -> int:
    welfare = await houses_in(session, town_id) * rules.welfare.poverty_relief
    located = select(EntityRow.id).where(EntityRow.location_id == town_id)
    pools = await session.scalars(select(CooperativeRow.purpose).where(CooperativeRow.faction_entity_id.in_(located), CooperativeRow.members > 0))
    cooperative = sum(rules.cooperatives.relief for purpose in pools if purpose in RELIEVING)
    return welfare + cooperative + await realm_relief(session, rules, town_id)


async def beggars(session: AsyncSession, rules: Rules, town_id: int, poverty: int) -> int:
    if poverty < rules.welfare.beggars_from or await houses_in(session, town_id):
        return 0
    return rules.welfare.beggars_insecurity


async def relieved_theft(session: AsyncSession, rules: Rules, town_id: int) -> float:
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    row = await session.get(PoorReliefRow, realm) if realm is not None else None
    return row.reach * rules.poor_relief.theft_pct / PERCENT / PERCENT if row is not None else 0.0


async def tavern_of(session: AsyncSession, town_id: int) -> TavernRow | None:
    hosted = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.host_entity_id == town_id)
    return await session.scalar(select(TavernRow).where(TavernRow.structure_entity_id.in_(hosted)).order_by(TavernRow.structure_entity_id).limit(1))


async def commute_share(session: AsyncSession, town_id: int) -> float:
    row = await session.get(CommuteRow, town_id)
    return 1 - row.labour_lost / PERCENT if row is not None else 1.0
