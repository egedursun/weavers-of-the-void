from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochEnginePhaseRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.epoch import EngineStage
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.engine.phases.mortals import mortal_aging
from aerona.engine.primitives.stats import stat
from aerona.services.integrity.chronology import born_children, rules_of

AGING_SLACK_SHARE = 5
AGING_PHASE = mortal_aging.__name__


async def aged_in(session: AsyncSession, epoch: int) -> bool:
    found = await session.scalar(
        select(EpochEnginePhaseRow.phase)
        .where(EpochEnginePhaseRow.epoch == epoch, EpochEnginePhaseRow.stage == EngineStage.TICK, EpochEnginePhaseRow.phase == AGING_PHASE)
        .limit(1)
    )
    return found is not None


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
    aged = await aged_in(session, epoch)
    years = rules.time.years_per_epoch
    for mortal, birth in rows:
        age = stat(mortal, "age")
        if mortal.id in children or held(mortal.id) or age is None or age <= 0 or "year" in (birth.locked or []):
            continue
        ended = stat(mortal, "death_year")
        until = int(ended) if ended is not None else (epoch_end_year(epoch, years) if aged else epoch_start_year(epoch, years)) - 1
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


async def births_pulled_by_a_misread_age(session: AsyncSession) -> dict[int, tuple[NodeBirthRow, int]]:
    rules, epoch = await rules_of(session)
    aged = await aged_in(session, epoch)
    years = rules.time.years_per_epoch
    slack = years // AGING_SLACK_SHARE
    pulled = await session.execute(
        select(StateChangeRow.node_id, StateChangeRow.before_number, StateChangeRow.after_number)
        .where(
            StateChangeRow.table_name == NodeBirthRow.__tablename__,
            StateChangeRow.field == "year",
            StateChangeRow.phase.is_(None),
            StateChangeRow.node_id.is_not(None),
            StateChangeRow.after_number < StateChangeRow.before_number,
        )
        .order_by(StateChangeRow.id)
    )
    last: dict[int, tuple[int, int]] = {}
    for node, before, after in pulled:
        if node is not None and before is not None and after is not None:
            last[node] = (int(before), int(after))
    found: dict[int, tuple[NodeBirthRow, int]] = {}
    for node, (before, after) in sorted(last.items()):
        mortal = await session.get(EntityRow, node)
        birth = await session.get(NodeBirthRow, node)
        age = stat(mortal, "age") if mortal is not None else None
        if mortal is None or birth is None or age is None or held(node) or birth.year != after or "year" in (birth.locked or []):
            continue
        ended = stat(mortal, "death_year")
        until = int(ended) if ended is not None else (epoch_end_year(epoch, years) if aged else epoch_start_year(epoch, years)) - 1
        if abs(before - (until - int(age))) <= slack:
            found[node] = (birth, before)
    return found


async def pulled_births(session: AsyncSession) -> list[int]:
    return sorted(await births_pulled_by_a_misread_age(session))


async def restore_pulled_birth(session: AsyncSession, mortal_id: int) -> None:
    found = (await births_pulled_by_a_misread_age(session)).get(mortal_id)
    if found is None:
        return
    birth, before = found
    birth.year, birth.season, birth.day, birth.hour = before, None, None, None
