from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import LeagueAim, LeagueDecisionKind, LeagueOrgan, LeagueStanding
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, aims_of, core_of, living_polity, members_of
from aerona.engine.leagues.decisions import lift_sanctions, propose
from aerona.engine.monetary.authorities import authority_of, currency_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record

COHESION_MIDPOINT = 50


async def pay_dues(ctx: TickContext, profile: PolityLeagueRow, members: list[LeagueMemberRow], tally: LeagueTally) -> list[LeagueMemberRow]:
    broke: list[LeagueMemberRow] = []
    for member in members:
        realm = await ctx.session.get(PolityProfileRow, member.polity_entity_id)
        if realm is None or held(member.polity_entity_id):
            continue
        dues = round_half_up(realm.treasury * profile.dues_pct / PERCENT)
        if dues <= 0 or not move_amount(realm, profile, "treasury", dues):
            broke.append(member)
            continue
        member.dues_paid += dues
    return broke


async def leave(ctx: TickContext, league: EntityRow, member: LeagueMemberRow, why: str, tally: LeagueTally) -> None:
    if "standing" in (member.locked or []):
        return
    await ctx.session.delete(member)
    tally.left += 1
    await record(ctx, "league.left", roles={IncidentRole.SUBJECT: member.polity_entity_id, IncidentRole.ACTOR: league.id}, facts={"why": why})


async def enemies_of(ctx: TickContext, core: int) -> list[int]:
    return [bond.target_node_id for bond in await BondRepository(ctx.session).outgoing(core, BondKind.ENEMY)]


async def guard(ctx: TickContext, profile: PolityLeagueRow, members: list[LeagueMemberRow]) -> None:
    cores = {await core_of(ctx.session, member.polity_entity_id): member for member in members}
    for core, member in sorted(((core, member) for core, member in cores.items() if core is not None), key=lambda item: item[0]):
        for enemy in await enemies_of(ctx, core):
            if enemy in cores:
                continue
            await propose(ctx, profile, LeagueDecisionKind.COMMON_FORCE, LeagueOrgan.FORCE, subject=enemy, proposer=member.polity_entity_id)
            return


async def strife(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, members: list[LeagueMemberRow]) -> bool:
    cores = {await core_of(ctx.session, member.polity_entity_id): member for member in members}
    for core, member in sorted(((core, member) for core, member in cores.items() if core is not None), key=lambda item: item[0]):
        for enemy in await enemies_of(ctx, core):
            if enemy in cores and enemy != core:
                await propose(ctx, profile, LeagueDecisionKind.MEDIATION, LeagueOrgan.COURT, subject=member.polity_entity_id, proposer=league.id)
                return True
    return False


async def unite_money(ctx: TickContext, profile: PolityLeagueRow, members: list[LeagueMemberRow], tally: LeagueTally) -> None:
    if LeagueAim.CURRENCY_UNION not in aims_of(profile):
        return
    authority = await ctx.session.get(MonetaryAuthorityRow, profile.authority_id) if profile.authority_id is not None else None
    if authority is None and members and "authority_id" not in (profile.locked or []):
        authority = await authority_of(ctx.session, await currency_for(ctx.session, members[0].polity_entity_id))
        profile.authority_id = authority.id if authority is not None else None
    if authority is None:
        return
    for member in members:
        towns = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == member.polity_entity_id)
        for society in await ctx.session.scalars(
            select(CommunitySocietyRow).where(CommunitySocietyRow.entity_id.in_(towns)).order_by(CommunitySocietyRow.entity_id)
        ):
            if society.currency_id != authority.currency_id and not held(society.entity_id):
                society.currency_id = authority.currency_id
                tally.adopted += 1


async def neighbours(ctx: TickContext, league: EntityRow, members: list[LeagueMemberRow]) -> list[EntityRow]:
    inside = {member.polity_entity_id for member in await members_of(ctx.session, league.id, frozenset(LeagueStanding))}
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == league.world_id)
    cores = {await core_of(ctx.session, member.polity_entity_id) for member in members}
    found: list[EntityRow] = []
    for polity in await ctx.session.scalars(query.order_by(EntityRow.id)):
        if polity.id in inside or held(polity.id):
            continue
        core = await core_of(ctx.session, polity.id)
        if core is not None and not set(await enemies_of(ctx, core)) & cores:
            found.append(polity)
    return found


async def grow(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, members: list[LeagueMemberRow]) -> None:
    if not ctx.rng(f"leagues.admit.{league.id}.{ctx.epoch}").chance(ctx.rules.leagues.admit_chance_pct):
        return
    candidates = await neighbours(ctx, league, members)
    if candidates:
        await propose(ctx, profile, LeagueDecisionKind.ADMIT, LeagueOrgan.ASSEMBLY, subject=candidates[0].id, proposer=league.id)


async def discipline(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, members: list[LeagueMemberRow], tally: LeagueTally) -> None:
    for member in members:
        if member.defiance >= ctx.rules.leagues.defiance_to_expel:
            await propose(ctx, profile, LeagueDecisionKind.EXPEL, LeagueOrgan.ASSEMBLY, subject=member.polity_entity_id, proposer=league.id)
            member.defiance = 0
            tally.defied += 1
        elif member.defiance and member.standing is not LeagueStanding.SUSPENDED and "standing" not in (member.locked or []):
            await propose(ctx, profile, LeagueDecisionKind.SANCTION, LeagueOrgan.COUNCIL, subject=member.polity_entity_id, proposer=league.id)
            member.standing = LeagueStanding.SUSPENDED
        elif not member.defiance and member.standing is LeagueStanding.SUSPENDED and "standing" not in (member.locked or []):
            member.standing = LeagueStanding.MEMBER
            await lift_sanctions(ctx, league.id, member.polity_entity_id)


async def worlds_apart(ctx: TickContext, members: list[LeagueMemberRow]) -> int:
    worlds = set()
    for member in members:
        polity = await ctx.session.get(EntityRow, member.polity_entity_id)
        if polity is not None and polity.world_id is not None:
            worlds.add(polity.world_id)
    if len(worlds) < 2:
        return 0
    realms = [member.polity_entity_id for member in members]
    towns = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id.in_(realms))))
    linked = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id.in_(sorted({*realms, *towns})))
    return 0 if await ctx.session.scalar(linked.limit(1)) is not None else len(worlds) - 1


async def measure(ctx: TickContext, league: EntityRow, profile: PolityLeagueRow, members: list[LeagueMemberRow], *, troubled: bool) -> None:
    table = ctx.rules.leagues
    if "depth" not in (profile.locked or []):
        profile.depth = clamp_int(profile.depth + (-table.depth_loss if troubled else table.depth_gain), 0, PERCENT)
    founders = [member for member in members if member.standing is LeagueStanding.FOUNDER]
    living = [await living_polity(ctx.session, member.polity_entity_id) for member in founders]
    leaderless = bool(founders) and all(polity is None for polity in living)
    strength = (
        table.strength_per_member * len(members) - table.interworld_strength_loss * await worlds_apart(ctx, members) - (table.depth_loss if leaderless else 0)
    )
    set_stats(
        league,
        strength=clamp_int(strength, 0, PERCENT),
        cohesion=clamp_int(COHESION_MIDPOINT + profile.depth // 2 - (table.depth_loss if troubled else 0), 0, PERCENT),
        members=len(members),
    )


async def dissolve(ctx: TickContext, league: EntityRow, why: str, tally: LeagueTally) -> None:
    tally.dissolved += 1
    for member in await members_of(ctx.session, league.id, frozenset(LeagueStanding)):
        await lift_sanctions(ctx, league.id, member.polity_entity_id)
    await record(ctx, "league.dissolved", roles={IncidentRole.SUBJECT: league.id}, facts={"why": why})
    await retire_in(ctx, league, why)
