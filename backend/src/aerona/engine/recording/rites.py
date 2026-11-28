from collections.abc import Sequence

from sqlalchemy import select

from aerona.catalog.incident_kinds.sequence import RITE_YEARS, SOON_AFTER_DEATH
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext
from aerona.engine.recording.births import born_floor
from aerona.engine.recording.deaths import mortal_floor


async def near_the_dead(ctx: TickContext, key: str, nodes: Sequence[int], moment: Moment, floor: Moment | None) -> Moment:
    if key not in SOON_AFTER_DEATH:
        return moment
    death = await mortal_floor(ctx.session, nodes)
    if death is None or moment.year <= death.year + RITE_YEARS:
        return moment
    first = min(nodes) if nodes else 0
    year = death.year + ctx.rng(f"rite_year.{key}.{first}.{death.year}").integer(0, RITE_YEARS)
    return Moment(year, moment.season, moment.day, moment.hour).at_least(floor)


async def first_death(ctx: TickContext, living: Sequence[int]) -> int | None:
    if not living:
        return None
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.id.in_(sorted(set(living))), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD)
        .order_by(EntityRow.id)
    )
    years = [year for row in rows if isinstance(year := getattr(row.stats, "death_year", None), int)]
    return min(years) if years else None


async def before_the_dead(ctx: TickContext, living: Sequence[int], nodes: Sequence[int], moment: Moment, floor: Moment | None) -> Moment:
    died = await first_death(ctx, living)
    if died is None or moment.year <= died:
        return moment
    posthumous = [node for node in nodes if node not in living]
    low = latest(floor, await born_floor(ctx.session, nodes), await mortal_floor(ctx.session, posthumous))
    if low is not None and low.year > died:
        return moment
    return Moment(died, moment.season, moment.day, moment.hour).at_least(low)
