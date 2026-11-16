from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import PROFILES, CohortKey, cohorts_of, row_for
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import blocked
from aerona.engine.primitives.numbers import apportion, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.transfers import move_amount

SICK_KEY = "sick"


def sick_share(book: DiseaseBook, community_id: int, region_id: int | None) -> float:
    table = book.rules.epidemiology
    share = 0.0
    for outbreak in book.outbreaks_in(region_id):
        profile = book.profiles.get(outbreak.disease_entity_id)
        if profile is None or outbreak.status is OutbreakStatus.ENDED:
            continue
        reach = outbreak.severity / PERCENT * min(2.0, profile.virulence / table.neutral_virulence) * table.infected_pct / PERCENT
        reach *= 1 - book.immune_share(community_id, outbreak.disease_entity_id) * table.immunity_strength_pct / PERCENT
        if outbreak.status is OutbreakStatus.WANING:
            reach *= table.waning_death_pct / PERCENT
        share += reach
    return min(table.sick_cap_pct / PERCENT, share * table.sick_share_pct / PERCENT)


def shift(ctx: TickContext, rows: dict[CohortKey, CohortRow], community_id: int, amount: int, *, falling: bool) -> int:
    source = CohortCondition.NONE if falling else CohortCondition.SICK
    target = CohortCondition.SICK if falling else CohortCondition.NONE
    profile = PROFILES[FlowCategory.PLAGUE]
    keys = sorted((key for key in rows if key[3] is source and rows[key].count > 0), key=lambda key: tuple(part.value for part in key))
    weights = {key: rows[key].count * (profile.get((key[0], key[1]), 1.0) if falling else 1.0) for key in keys}
    mass = sum(weights.values())
    if mass <= 0 or amount <= 0:
        return 0
    moved = 0
    parts = apportion(amount, weights)
    for key in keys:
        part = max(0, min(rows[key].count, parts.get(key, 0), amount - moved))
        if part <= 0:
            continue
        if move_amount(rows[key], row_for(ctx.session, rows, community_id, (key[0], key[1], key[2], target), ctx.epoch), "count", part):
            moved += part
    return moved


async def sicken_cohorts(ctx: TickContext, book: DiseaseBook) -> tuple[int, int]:
    struck = {community_id for outbreak in book.outbreaks for community_id in book.atlas.communities_in(outbreak.region_entity_id)}
    lying = set(await ctx.session.scalars(select(CohortRow.community_entity_id).where(CohortRow.condition == CohortCondition.SICK, CohortRow.count > 0)))
    fell = recovered = 0
    for community_id in sorted(struck | lying):
        if blocked(community_id, SICK_KEY) or await living_entity(ctx.session, community_id) is None:
            continue
        rows = await cohorts_of(ctx.session, community_id)
        if not rows:
            continue
        people = sum(row.count for row in rows.values())
        sick = sum(row.count for key, row in rows.items() if key[3] is CohortCondition.SICK)
        wanted = round_half_up(people * sick_share(book, community_id, book.atlas.top_region(community_id)))
        if wanted > sick:
            fell += shift(ctx, rows, community_id, wanted - sick, falling=True)
        elif wanted < sick:
            recovered += shift(ctx, rows, community_id, sick - wanted, falling=False)
    return fell, recovered
