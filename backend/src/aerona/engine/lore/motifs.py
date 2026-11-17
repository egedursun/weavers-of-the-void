from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.motifs import MOTIF_SOURCES
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.demography import MotifSource

MOTIFS_HELD = 3


async def canon_motifs(session: AsyncSession, people: EntityRow) -> list[MotifSource]:
    if people.world_id is None:
        return [MotifSource.PATTERN]
    counted = await session.execute(
        select(EntityRow.entity_type, EntityRow.status, func.count(EntityRow.id))
        .where(EntityRow.world_id == people.world_id)
        .group_by(EntityRow.entity_type, EntityRow.status)
    )
    present = {(kind, status): count for kind, status, count in counted.all()}
    weights = {source: sum(present.get((kind, spec.status), 0) for kind in spec.entity_types) for source, spec in MOTIF_SOURCES.items() if spec.entity_types}
    order = list(MotifSource)
    turn = people.id % len(order)
    rotated = order[turn:] + order[:turn]
    ranked = sorted((source for source in rotated if weights.get(source, 0) > 0), key=lambda source: -weights[source])
    return ranked[:MOTIFS_HELD] or [MotifSource.PATTERN]


def motifs_of(culture: PeopleCultureRow | None) -> list[MotifSource]:
    if culture is None:
        return []
    return [MotifSource(value) for value in culture.motif_sources if value in MotifSource._value2member_map_]


async def people_motifs(session: AsyncSession, people_id: int | None) -> list[MotifSource]:
    return motifs_of(await session.get(PeopleCultureRow, people_id)) if people_id is not None else []
