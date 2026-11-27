from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.primitives.stats import stat
from aerona.services.integrity.chronology import born_children, rules_of

AGING_SLACK_SHARE = 5


async def lived_years_of(session: AsyncSession) -> dict[int, tuple[NodeBirthRow, int]]:
    rules, epoch = await rules_of(session)
    children = await born_children(session)
    found: dict[int, tuple[NodeBirthRow, int]] = {}
    rows = await session.execute(
        select(EntityRow, NodeBirthRow)
        .join(NodeBirthRow, NodeBirthRow.node_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL)
        .order_by(EntityRow.id)
    )
    for mortal, birth in rows:
        age = stat(mortal, "age")
        if mortal.id in children or held(mortal.id) or age is None or age <= 0 or "year" in (birth.locked or []):
            continue
        ended = stat(mortal, "death_year")
        until = int(ended) if ended is not None else epoch_start_year(epoch, rules.time.years_per_epoch) - 1
        lived = until - int(age)
        if birth.year > lived + rules.time.years_per_epoch // AGING_SLACK_SHARE:
            found[mortal.id] = (birth, lived)
    return found


async def adults_born_at_first_sight(session: AsyncSession) -> list[int]:
    return sorted(await lived_years_of(session))


async def date_adult_birth(session: AsyncSession, mortal_id: int) -> None:
    found = (await lived_years_of(session)).get(mortal_id)
    if found is None:
        return
    birth, lived = found
    birth.year, birth.season, birth.day, birth.hour = lived, None, None, None
