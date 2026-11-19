from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmography import CelestialReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.engine.body.customs import people_of
from aerona.rules.registry import Rules

SKYWARD = (FolkDomain.SKY, FolkDomain.WEATHER)


async def best_accuracy(session: AsyncSession, people_id: int, domains: tuple[FolkDomain, ...] = SKYWARD) -> int:
    best = await session.scalar(
        select(func.max(ObservationMethodRow.accuracy)).where(ObservationMethodRow.people_entity_id == people_id, ObservationMethodRow.domain.in_(domains))
    )
    return int(best or 0)


async def sky_marks(session: AsyncSession, rules: Rules, people_id: int) -> int:
    watched = await session.scalar(
        select(func.count()).select_from(CelestialReadingRow).where(CelestialReadingRow.people_entity_id == people_id, CelestialReadingRow.visible.is_(True))
    )
    return min(rules.forecasting.sky_mark_cap, int(watched or 0) * rules.forecasting.sky_mark_accuracy)


async def sky_omens(session: AsyncSession, people_id: int) -> int:
    readings = await session.execute(
        select(CelestialReadingRow.reading, func.count())
        .where(CelestialReadingRow.people_entity_id == people_id, CelestialReadingRow.visible.is_(True))
        .group_by(CelestialReadingRow.reading)
    )
    counted = {reading: int(count) for reading, count in readings}
    return counted.get(OmenReading.GOOD, 0) - counted.get(OmenReading.EVIL, 0)


async def observation_bonus(session: AsyncSession, rules: Rules, town: EntityRow) -> int:
    folk = await people_of(session, town)
    if folk is None:
        return 0
    reading = min(PERCENT, await best_accuracy(session, folk.id) + await sky_marks(session, rules, folk.id))
    return reading * rules.forecasting.navigation_share_pct // PERCENT
