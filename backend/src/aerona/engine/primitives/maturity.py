from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import LIFE_STAGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import PrisonerRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mortal import StressBreak
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.rules.registry import Rules

UNDER_AGE = having(LIFE_STAGE_TRAITS, LifeStageTrait.UNDER_AGE)


def of_age_query() -> ColumnElement[bool]:
    return EntityRow.id.not_in(select(MortalProfileRow.entity_id).where(MortalProfileRow.life_stage.in_(sorted(UNDER_AGE))))


async def under_age(session: AsyncSession, ids: Iterable[int | None]) -> set[int]:
    wanted = sorted({node for node in ids if node is not None})
    if not wanted:
        return set()
    statement = select(MortalProfileRow.entity_id).where(MortalProfileRow.entity_id.in_(wanted), MortalProfileRow.life_stage.in_(sorted(UNDER_AGE)))
    return set(await session.scalars(statement))


async def of_age(session: AsyncSession, node_id: int | None) -> bool:
    return node_id is not None and node_id not in await under_age(session, [node_id])


async def of_age_among(session: AsyncSession, mortals: Sequence[EntityRow]) -> list[EntityRow]:
    young = await under_age(session, [mortal.id for mortal in mortals])
    return [mortal for mortal in mortals if mortal.id not in young]


def office_age_share(rules: Rules, mortal: EntityRow, ahead: int = 0) -> int:
    table = rules.peoples
    span = getattr(mortal.stats, "lifespan", None) or table.maturity_years + table.adult_years + table.elder_years
    age = (getattr(mortal.stats, "age", None) or 0) + ahead
    return max(0, min(PERCENT, age * PERCENT // max(1, span)))


def past_office_age(rules: Rules, mortal: EntityRow, ahead: int = 0) -> bool:
    return office_age_share(rules, mortal, ahead) >= rules.departures.retirement_age_share_pct


async def withdrawn_among(session: AsyncSession, ids: Iterable[int | None]) -> set[int]:
    wanted = sorted({node for node in ids if node is not None})
    if not wanted:
        return set()
    statement = select(MortalProfileRow.entity_id).where(
        MortalProfileRow.entity_id.in_(wanted), MortalProfileRow.last_break == StressBreak.WITHDRAWAL, MortalProfileRow.last_break_epoch >= 0
    )
    return set(await session.scalars(statement))


async def away_among(session: AsyncSession, ids: Iterable[int | None]) -> set[int]:
    wanted = sorted({node for node in ids if node is not None})
    if not wanted:
        return set()
    hiding = select(FugitiveRow.mortal_entity_id).where(
        FugitiveRow.mortal_entity_id.in_(wanted), FugitiveRow.caught_epoch.is_(None), FugitiveRow.freed_epoch.is_(None)
    )
    jailed = select(PrisonerRow.mortal_entity_id).where(PrisonerRow.mortal_entity_id.in_(wanted))
    taken = select(CaptiveRow.captive_entity_id).where(CaptiveRow.captive_entity_id.in_(wanted), CaptiveRow.status == CaptiveStatus.HELD)
    away = await withdrawn_among(session, wanted)
    for statement in (hiding, jailed, taken):
        away |= set(await session.scalars(statement))
    return away


async def acting_for(session: AsyncSession, realm_id: int, ruler_id: int | None) -> int | None:
    if ruler_id is None or await of_age(session, ruler_id):
        return ruler_id
    return await session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.REGENT, OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
        .limit(1)
    )
