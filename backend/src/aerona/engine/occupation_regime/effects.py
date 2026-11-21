from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationMeasureRow, OccupationRegimeRow
from aerona.domain.enums.occupation_regimes import CollaborationFate, CollaborationKind, OccupationMeasure
from aerona.rules.registry import Rules

M = OccupationMeasure
PARTISAN_WEIGHT = total(
    OccupationMeasure,
    {
        M.CURFEW: 60,
        M.HOSTAGES: 100,
        M.COLLECTIVE_PUNISHMENT: 100,
        M.DEPORTATION: 80,
        M.REQUISITION: 20,
        M.BAN_ON_GATHERING: 70,
        M.AMNESTY_OFFER: 40,
    },
)
INTELLIGENCE = frozenset({CollaborationKind.INFORMING, CollaborationKind.POLICE})
DAMPING_CAP = 80


async def regime_over(session: AsyncSession, region_id: int) -> OccupationRegimeRow | None:
    query = select(OccupationRegimeRow).where(OccupationRegimeRow.region_entity_id == region_id, OccupationRegimeRow.ended_epoch.is_(None))
    return await session.scalar(query.order_by(OccupationRegimeRow.id).limit(1))


async def serving(session: AsyncSession, regime_id: int) -> list[CollaborationRow]:
    query = select(CollaborationRow).where(CollaborationRow.regime_id == regime_id, CollaborationRow.fate == CollaborationFate.SERVING)
    return list(await session.scalars(query.order_by(CollaborationRow.id)))


async def active_measures(session: AsyncSession, regime_id: int) -> list[OccupationMeasureRow]:
    query = select(OccupationMeasureRow).where(OccupationMeasureRow.regime_id == regime_id, OccupationMeasureRow.ended_epoch.is_(None))
    return list(await session.scalars(query.order_by(OccupationMeasureRow.id)))


async def partisan_share(session: AsyncSession, rules: Rules, region_id: int) -> float:
    regime = await regime_over(session, region_id)
    if regime is None:
        return 1.0
    table = rules.occupation
    informers = sum(1 for row in await serving(session, regime.id) if row.kind in INTELLIGENCE)
    intel = min(DAMPING_CAP, informers * table.collaborator_intel_pct)
    weight = sum(PARTISAN_WEIGHT[row.measure] * row.strength for row in await active_measures(session, regime.id)) // PERCENT
    measures = min(DAMPING_CAP, weight * table.measure_partisan_cut_pct // PERCENT)
    return (1 - intel / PERCENT) * (1 - measures / PERCENT)


def capped(rules: Rules, share: int) -> int:
    return max(0, min(share, rules.occupation.extraction_cap_pct))


async def tax_share(session: AsyncSession, rules: Rules, region_id: int) -> int:
    regime = await regime_over(session, region_id)
    return rules.occupation.tax_pct if regime is None else capped(rules, regime.tax_pct)


async def levy_share(session: AsyncSession, region_id: int) -> int:
    regime = await regime_over(session, region_id)
    return PERCENT if regime is None else regime.levy_pct
