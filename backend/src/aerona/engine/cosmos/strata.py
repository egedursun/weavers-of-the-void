from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.strata import hosts_for
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.faith import StratumActivity, StratumValence

STRATA_FIXUP = "cosmography.strata_hosts"
DRAWING_DOMAINS = frozenset({Domain.DEATH, Domain.SLEEP})


def host_for(dimensions: Iterable[DimensionRow], valence: StratumValence, activity: StratumActivity) -> DimensionRow | None:
    hosts = hosts_for(valence, activity)
    fitting = sorted((row for row in dimensions if row.dimension_kind in hosts), key=lambda row: (hosts.index(row.dimension_kind), row.id))
    return next((row for row in fitting if not held(row.id)), None)


async def host_strata(session: AsyncSession) -> int:
    dimensions = list(await session.scalars(select(DimensionRow).order_by(DimensionRow.id)))
    if not dimensions:
        return 0
    hosted = 0
    for row in await session.scalars(select(AfterlifeStratumRow).where(AfterlifeStratumRow.dimension_id.is_(None)).order_by(AfterlifeStratumRow.id)):
        if held(row.realm_entity_id):
            continue
        host = host_for(dimensions, row.valence, row.activity)
        if host is not None:
            row.dimension_id = host.id
            hosted += 1
    await session.flush()
    return hosted


async def host_strata_once(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, STRATA_FIXUP) is not None:
        return 0
    hosted = await host_strata(session)
    session.add(AppliedFixupRow(key=STRATA_FIXUP, result={"hosted": hosted}))
    await session.flush()
    return hosted


async def drawing_dimensions(session: AsyncSession) -> set[int]:
    drawing: set[int] = set()
    for dimension in await session.scalars(select(DimensionRow).where(DimensionRow.ruler_node_id.is_not(None))):
        son = await session.get(SonRow, dimension.ruler_node_id)
        if son is not None and {son.domain_primary, son.domain_secondary} & DRAWING_DOMAINS:
            drawing.add(dimension.id)
    return drawing
