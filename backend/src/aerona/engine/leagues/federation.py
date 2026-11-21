from sqlalchemy import delete, select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.leagues import LeagueAim
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import GovernmentKind
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, aims_of, core_of
from aerona.engine.leagues.life import dissolve
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity
from aerona.engine.primitives.records import retire_in
from aerona.engine.recording.record import record

FEDERATING_AIMS = (frozenset({LeagueAim.DEFENCE, LeagueAim.CUSTOMS_UNION}), frozenset({LeagueAim.DEFENCE, LeagueAim.TRADE}))


def federating(profile: PolityLeagueRow, depth_threshold: int) -> bool:
    aims = aims_of(profile)
    return profile.depth >= depth_threshold and any(wanted <= aims for wanted in FEDERATING_AIMS)


async def federate(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, members: list[LeagueMemberRow], tally: LeagueTally) -> EntityRow | None:
    if any(held(member.polity_entity_id) for member in members):
        return None
    seat = await ctx.session.get(EntityRow, profile.seat_entity_id) if profile.seat_entity_id is not None else None
    if seat is None:
        core = await core_of(ctx.session, members[0].polity_entity_id)
        seat = await ctx.session.get(EntityRow, core) if core is not None else None
    if seat is None:
        return None
    realm = await found_polity(ctx, await RealmBook.load(ctx.session), seat, told=False)
    realm.profile.government = GovernmentKind.FEDERATION
    joined: list[int] = []
    for member in members:
        towns = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == member.polity_entity_id)))
        await ctx.session.execute(delete(PolityMemberRow).where(PolityMemberRow.polity_entity_id == member.polity_entity_id))
        for town in sorted(set(towns)):
            ctx.session.add(PolityMemberRow(polity_entity_id=realm.entity.id, member_entity_id=town, joined_epoch=ctx.epoch))
        polity = await ctx.session.get(EntityRow, member.polity_entity_id)
        old = await ctx.session.get(PolityProfileRow, member.polity_entity_id)
        if old is not None:
            realm.profile.treasury += old.treasury
            old.treasury = 0
        if polity is not None:
            await retire_in(ctx, polity, f"it joined the federation of {realm.entity.name}")
            joined.append(polity.id)
    realm.profile.treasury += profile.treasury
    profile.treasury = 0
    tally.federated += 1
    await record(
        ctx,
        "league.federated",
        roles={IncidentRole.PREDECESSOR: league.id, IncidentRole.SUCCESSOR: realm.entity.id, IncidentRole.MEMBER: joined},
        facts={"members": len(joined)},
    )
    await dissolve(ctx, league, f"it became the federation of {realm.entity.name}", tally)
    return realm.entity
