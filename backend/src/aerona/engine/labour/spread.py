from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.labour import LabourDisputeRow
from aerona.db.tables.media import MediaOutletRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.labour import DisputeOutcome
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import LabourTally, body_covering
from aerona.engine.labour.founding import form_for, found_body
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity

REACH_SHARE = 4


async def neighbours(ctx: TickContext, town_id: int) -> list[int]:
    realms = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id)
    query = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id.in_(realms), PolityMemberRow.member_entity_id != town_id)
    return sorted(set(await ctx.session.scalars(query)))


async def spread_from(ctx: TickContext, dispute: LabourDisputeRow, tally: LabourTally) -> int | None:
    town = dispute.settlement_entity_id
    if dispute.outcome is not DisputeOutcome.WON or town is None:
        return None
    reach = await ctx.session.scalar(select(func.max(MediaOutletRow.reach)).where(MediaOutletRow.seat_entity_id == town)) or 0
    chance = clamp_int(ctx.rules.labour.spread_chance_pct + reach // REACH_SHARE, 0, PERCENT)
    if not ctx.rng(f"labour.spread.{dispute.id}").chance(chance):
        return None
    working = set(await ctx.session.scalars(select(LabourRow.community_entity_id).where(LabourRow.job == dispute.trade, LabourRow.workers > 0)))
    places = [place for place in await neighbours(ctx, town) if place in working and not held(place)]
    if not places:
        return None
    place = ctx.rng(f"labour.spread.place.{dispute.id}").pick(places)
    body = await body_covering(ctx.session, place, dispute.trade)
    if body is not None:
        if "solidarity" not in (body.locked or []):
            body.solidarity = clamp_int(body.solidarity + ctx.rules.labour.solidarity_won, 0, PERCENT)
        tally.spread += 1
        return place
    community = await living_entity(ctx.session, place)
    if community is None:
        return None
    await found_body(ctx, community, [dispute.trade], await form_for(ctx, place, dispute.trade))
    tally.spread += 1
    tally.founded += 1
    return place
