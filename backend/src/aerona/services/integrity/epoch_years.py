from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.rules.registry import Rules


async def align_epoch_years(session: AsyncSession, rules: Rules) -> int:
    years = rules.time.years_per_epoch
    changed = 0
    for row in await session.scalars(select(EpochRow)):
        start, end = epoch_start_year(row.epoch, years), epoch_end_year(row.epoch, years) - 1
        if (row.year_start, row.year_end) != (start, end):
            row.year_start, row.year_end = start, end
            changed += 1
    for line in await session.scalars(select(ChronicleRow).where(ChronicleRow.year.is_not(None))):
        start = epoch_start_year(line.epoch, years)
        last = epoch_end_year(line.epoch, years) - 1
        if line.year is not None and not start <= line.year <= last:
            line.year = max(start, min(last, line.year))
            changed += 1
    cosmos = await session.get(CosmosRow, 1)
    if cosmos is not None and cosmos.epoch_start_year != epoch_start_year(cosmos.epoch, years):
        cosmos.epoch_start_year = epoch_start_year(cosmos.epoch, years)
        changed += 1
    await session.flush()
    return changed
