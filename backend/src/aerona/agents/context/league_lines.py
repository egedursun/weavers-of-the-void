from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.engine.leagues.book import aims_of, members_of
from aerona.engine.primitives.stats import stat_or

RECENT_DECISIONS = 3


async def mortal_league_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    if me.location_id is None:
        return []
    realm = await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    if realm is None:
        return []
    found: list[str] = []
    rows = select(LeagueMemberRow).where(LeagueMemberRow.polity_entity_id == realm).order_by(LeagueMemberRow.id)
    for row in await session.scalars(rows):
        league = await session.get(EntityRow, row.league_entity_id)
        profile = await session.get(PolityLeagueRow, row.league_entity_id)
        if league is None or profile is None:
            continue
        members = ", ".join([await named(scope, member.polity_entity_id) for member in await members_of(session, league.id)])
        aims = ", ".join(spoken(aim) for aim in sorted(aims_of(profile), key=lambda aim: aim.value)) or "no aims"
        found.append(
            f"your realm stands as {spoken(row.standing)} in {league.name} (league {league.id}), bound for {aims}, deciding {spoken(profile.vote_basis)}, "
            f"strength {stat_or(league, 'strength', 0)}, depth {profile.depth}, dues {profile.dues_pct} in a hundred; members: {members}"
        )
        recent = select(LeagueDecisionRow).where(LeagueDecisionRow.league_entity_id == league.id).order_by(LeagueDecisionRow.id.desc()).limit(RECENT_DECISIONS)
        for decision in await session.scalars(recent):
            about = f" on {await named(scope, decision.subject_node_id)}" if decision.subject_node_id is not None else ""
            found.append(f"{league.name} {spoken(decision.outcome)} {spoken(decision.kind)}{about} in its {spoken(decision.organ)}")
    return found
