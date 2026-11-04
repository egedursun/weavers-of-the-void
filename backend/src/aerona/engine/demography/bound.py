from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, row_for, total
from aerona.engine.primitives.numbers import round_half_up

BOUND = SocialClass.SERF_OR_SLAVE


def bound_share(rows: dict[CohortKey, CohortRow]) -> float:
    people = total(rows)
    bound = sum(row.count for key, row in rows.items() if key[2] is BOUND)
    return bound / people if people else 0.0


def sync_bound_share(society: CommunitySocietyRow | None, rows: dict[CohortKey, CohortRow]) -> None:
    if society is None:
        return
    current = society.share(BOUND)
    target = round(bound_share(rows) * PERCENT, 2)
    if abs(current - target) < 0.01:
        return
    others = [social_class for social_class in SocialClass if social_class is not BOUND]
    free = sum(society.share(social_class) for social_class in others) or 1.0
    for social_class in others:
        setattr(society, f"share_{social_class.value}", round(society.share(social_class) * (PERCENT - target) / free, 2))
    society.share_serf_or_slave = target


async def move_people(
    ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], *, source: SocialClass, target: SocialClass, share: float
) -> int:
    moved = 0
    for key in sorted(rows, key=lambda item: tuple(part.value for part in item)):
        band, sex, social_class, condition = key
        if social_class is not source or rows[key].count <= 0:
            continue
        count = round_half_up(rows[key].count * share)
        if count <= 0:
            continue
        rows[key].count -= count
        landed = CohortCondition.NONE if condition in {CohortCondition.ENSLAVED, CohortCondition.CAPTIVE} else condition
        row_for(ctx.session, rows, community.id, (band, sex, target, landed), ctx.epoch).count += count
        moved += count
    return moved
