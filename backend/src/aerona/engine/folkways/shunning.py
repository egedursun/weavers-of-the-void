from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import ImpuritySourceRow, PurityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.folkways import ImpuritySource, PurityState
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.folk import towns_of_people
from aerona.rules.registry import Rules

SICK_SOURCES = (ImpuritySource.THE_DEAD, ImpuritySource.BODILY_FLUIDS)


async def shunned_sick(session: AsyncSession) -> dict[int, int]:
    weights: dict[int, int] = {}
    for people_id, weight in await session.execute(
        select(ImpuritySourceRow.people_entity_id, ImpuritySourceRow.weight).where(ImpuritySourceRow.source.in_(list(SICK_SOURCES)))
    ):
        weights[people_id] = max(weights.get(people_id, 0), weight)
    if not weights:
        return {}
    towns = {town: people for people in sorted(weights) for town in await towns_of_people(session, people)}
    return {**weights, **{town: weights[people] for town, people in towns.items()}}


async def outsider_weight(session: AsyncSession, people_id: int) -> int:
    row = await session.get(ImpuritySourceRow, (people_id, ImpuritySource.OUTSIDERS))
    return row.weight if row is not None else 0


async def trading_post_at(session: AsyncSession, town_ids: tuple[int, int]) -> bool:
    found = await session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .where(
            StructureProfileRow.kind == StructureKind.KONTOR,
            StructureProfileRow.construction_state == ConstructionState.COMPLETE,
            StructureProfileRow.host_entity_id.in_(list(town_ids)),
        )
        .limit(1)
    )
    return found is not None


async def outsider_barrier(session: AsyncSession, rules: Rules, first: int, second: int) -> float:
    one, two = await session.get(EntityRow, first), await session.get(EntityRow, second)
    folks = [await people_of(session, town) if town is not None else None for town in (one, two)]
    if folks[0] is None or folks[1] is None or folks[0].id == folks[1].id:
        return 1.0
    weight = max(await outsider_weight(session, folks[0].id), await outsider_weight(session, folks[1].id))
    if not weight or await trading_post_at(session, (first, second)):
        return 1.0
    return max(0.0, 1 - weight * rules.purity.outsider_trade_pct / PERCENT / PERCENT)


async def corpse_exposure(session: AsyncSession, rules: Rules, mortal_id: int) -> float:
    row = await session.get(PurityRow, mortal_id)
    if row is None or row.state is PurityState.PURE or row.source is not ImpuritySource.THE_DEAD:
        return 1.0
    return 1 + rules.purity.corpse_exposure_pct / PERCENT
