from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import PolityLeagueRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, living_polity, members_of
from aerona.engine.leagues.decisions import pending, vote
from aerona.engine.leagues.federation import federate, federating
from aerona.engine.leagues.life import discipline, dissolve, grow, guard, leave, measure, pay_dues, strife, unite_money
from aerona.engine.leagues.rise import apply_legacy, maybe_found


async def tend_league(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, tally: LeagueTally) -> None:
    table = ctx.rules.leagues
    members = [member for member in await members_of(ctx.session, league.id) if await living_polity(ctx.session, member.polity_entity_id) is not None]
    if len(members) < table.found_min_members:
        await dissolve(ctx, league, "too few realms were left in it", tally)
        return
    broke = await pay_dues(ctx, profile, members, tally)
    for member in broke:
        if ctx.rng(f"leagues.exit.{league.id}.{member.polity_entity_id}.{ctx.epoch}").chance(table.exit_chance_pct):
            await leave(ctx, league, member, "it could not pay its dues", tally)
            members.remove(member)
    await guard(ctx, profile, members)
    troubled = await strife(ctx, league, profile, members)
    await unite_money(ctx, profile, members, tally)
    await grow(ctx, league, profile, members)
    for decision in await pending(ctx, league.id):
        await vote(ctx, profile, decision, tally)
    await discipline(ctx, league, profile, members, tally)
    troubled = troubled or any(member.defiance for member in members)
    await measure(ctx, league, profile, members, troubled=troubled)
    if federating(profile, table.federate_depth_threshold):
        await federate(ctx, league, profile, members, tally)


async def tend_leagues(ctx: TickContext) -> LeagueTally:
    tally = LeagueTally()
    await apply_legacy(ctx, tally)
    await maybe_found(ctx, tally)
    for profile in list(await ctx.session.scalars(select(PolityLeagueRow).order_by(PolityLeagueRow.league_entity_id))):
        league = await ctx.session.get(EntityRow, profile.league_entity_id)
        if league is None or league.status is not EntityStatus.CANON or held(league.id):
            continue
        await tend_league(ctx, league, profile, tally)
    return tally
