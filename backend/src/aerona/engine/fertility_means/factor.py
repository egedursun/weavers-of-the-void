from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.reproduction import SEX_KINDS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.fertility_means import FertilityMeans
from aerona.engine.mortal.life import sex_of_stats
from aerona.rules.registry import Rules

F = FertilityMeans
PREVENTING = frozenset({F.PREVENTION, F.ENDING_PREGNANCY})
CARRIED = frozenset({F.ENDING_PREGNANCY})


def fits_body(means: FertilityMeans, mortal: EntityRow, fertility: int | None) -> bool:
    if fertility is not None and fertility <= 0 and means in PREVENTING:
        return False
    return means not in CARRIED or SEX_KINDS[sex_of_stats(mortal)].bears


DIRECTION = total(
    FertilityMeans,
    {F.PREVENTION: -1, F.ENDING_PREGNANCY: -1, F.REMEDY_FOR_BARRENNESS: 1, F.ASSISTED_CONCEPTION: 1, F.SURROGACY: 1, F.MADE_BIRTH: 1},
)


def effect(rules: Rules, means: FertilityMeans, reliability: int) -> float:
    table = rules.fertility_means
    share = reliability / PERCENT
    if means is F.PREVENTION:
        return -share
    if means is F.ENDING_PREGNANCY:
        return -share * table.ending_pct / PERCENT
    return share * table.remedy_success_pct / PERCENT


async def conceives(session: AsyncSession, people_id: int | None) -> bool:
    if people_id is None:
        return True
    rows = list(
        await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == people_id, BodySystemRow.system == BodySystem.REPRODUCTION))
    )
    return not rows or any(row.present for row in rows)


@memoized(FertilityMeansRow)
async def means_by_people(session: AsyncSession) -> dict[int, list[FertilityMeansRow]]:
    found: dict[int, list[FertilityMeansRow]] = {}
    for row in await session.scalars(select(FertilityMeansRow).order_by(FertilityMeansRow.people_entity_id, FertilityMeansRow.means)):
        found.setdefault(row.people_entity_id, []).append(row)
    return found


async def means_of(session: AsyncSession, people_id: int) -> list[FertilityMeansRow]:
    return list((await means_by_people(session)).get(people_id, []))


async def people_factor(session: AsyncSession, rules: Rules, people_id: int | None) -> float:
    if people_id is None or not await conceives(session, people_id):
        return 1.0
    factor = 1.0
    for row in await means_of(session, people_id):
        factor *= 1 + effect(rules, row.means, row.reliability) * row.use_pct / PERCENT
    return max(0.0, factor)


async def user_factor(session: AsyncSession, rules: Rules, user: EntityRow) -> float:
    factor = 1.0
    for use in await session.scalars(select(FertilityUseRow).where(FertilityUseRow.user_entity_id == user.id).order_by(FertilityUseRow.id)):
        known = await session.get(FertilityMeansRow, (use.people_entity_id, use.means))
        if known is not None:
            factor *= 1 + effect(rules, use.means, known.reliability)
    return max(0.0, factor)
