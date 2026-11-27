from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import definite
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow, PolityLeagueRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.leagues import LeagueDecisionKind, LeagueDecisionOutcome, LeagueOrgan, LeagueStanding, LeagueVoteBasis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import held_coin
from aerona.engine.finance.credit import realm_of
from aerona.engine.leagues.book import LeagueTally, core_of, living_polity, membership, voters_of
from aerona.engine.leagues.founding import join
from aerona.engine.polity.laws import repeal
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.war import declare_war
from aerona.engine.services.war_resolution import make_peace

AGAINST_SUBJECT = frozenset({LeagueDecisionKind.EXPEL, LeagueDecisionKind.SANCTION, LeagueDecisionKind.COMMON_FORCE, LeagueDecisionKind.RULING})


def organ_for(profile: PolityLeagueRow, wanted: LeagueOrgan) -> LeagueOrgan | None:
    organs = set(profile.organs or [])
    if wanted.value in organs:
        return wanted
    return LeagueOrgan.ASSEMBLY if LeagueOrgan.ASSEMBLY.value in organs else None


async def propose(
    ctx: TickContext, profile: PolityLeagueRow, kind: LeagueDecisionKind, organ: LeagueOrgan, *, subject: int | None, proposer: int | None, rate: int = 0
) -> LeagueDecisionRow | None:
    chosen = organ_for(profile, organ)
    if chosen is None:
        return None
    decision = LeagueDecisionRow(
        league_entity_id=profile.league_entity_id,
        organ=chosen,
        kind=kind,
        subject_node_id=subject,
        proposer_node_id=proposer,
        rate_pct=clamp_int(rate, 0, PERCENT),
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(decision)
    await ctx.session.flush()
    return decision


async def weight(ctx: TickContext, basis: LeagueVoteBasis, member: LeagueMemberRow) -> int:
    if basis is LeagueVoteBasis.BY_POPULATION:
        polity = await ctx.session.get(EntityRow, member.polity_entity_id)
        return max(1, stat_or(polity, "subjects", 1)) if polity is not None else 1
    if basis is LeagueVoteBasis.BY_DUES:
        return max(1, member.dues_paid)
    if basis is LeagueVoteBasis.BY_VETO_HOLDERS:
        return 1 if member.veto else 0
    return 1


async def ballot(ctx: TickContext, profile: PolityLeagueRow, decision: LeagueDecisionRow, member: LeagueMemberRow) -> bool:
    if member.polity_entity_id == decision.subject_node_id:
        return decision.kind not in AGAINST_SUBJECT
    chance = ctx.rules.leagues.obedience_base_pct
    return ctx.rng(f"leagues.vote.{decision.id}.{member.polity_entity_id}").chance(chance)


async def vote(ctx: TickContext, profile: PolityLeagueRow, decision: LeagueDecisionRow, tally: LeagueTally) -> LeagueDecisionOutcome:
    if decision.outcome is not LeagueDecisionOutcome.PENDING or "outcome" in (decision.locked or []):
        return decision.outcome
    votes_for = votes_against = 0
    vetoed = False
    for member in await voters_of(ctx.session, profile.league_entity_id):
        weighed = await weight(ctx, profile.vote_basis, member)
        if await ballot(ctx, profile, decision, member):
            votes_for += weighed
        else:
            votes_against += weighed
            vetoed = vetoed or member.veto
    decision.votes_for, decision.votes_against = votes_for, votes_against
    decision.outcome = LeagueDecisionOutcome.VETOED if vetoed else LeagueDecisionOutcome.PASSED if votes_for > votes_against else LeagueDecisionOutcome.FAILED
    tally.decisions += 1
    if decision.outcome is LeagueDecisionOutcome.PASSED:
        await carry(ctx, profile, decision, tally)
    return decision.outcome


async def obeys(ctx: TickContext, league: EntityRow, member: LeagueMemberRow, key: str) -> bool:
    strength = stat_or(league, "strength", 0)
    chance = clamp_int(ctx.rules.leagues.obedience_base_pct * (PERCENT + strength) // (2 * PERCENT), 0, PERCENT)
    if ctx.rng(f"leagues.obey.{key}.{member.polity_entity_id}.{ctx.epoch}").chance(chance):
        return True
    member.defiance += 1
    return False


async def sanction(ctx: TickContext, league: EntityRow, target: int, tally: LeagueTally) -> None:
    ctx.session.add(
        TradePolicyRow(
            issuer_node_id=league.id,
            kind=TradePolicyKind.SANCTION,
            partner_node_id=target,
            rate_pct=ctx.rules.leagues.sanction_trade_cut_pct,
            since_epoch=ctx.epoch,
            reason=f"sanctioned by {league.name}",
            locked=[],
        )
    )
    tally.sanctions += 1
    await record(
        ctx, "league.sanction", roles={IncidentRole.ACTOR: league.id, IncidentRole.TARGET: target}, facts={"cut": ctx.rules.leagues.sanction_trade_cut_pct}
    )


async def lift_sanctions(ctx: TickContext, league_id: int, target: int) -> None:
    await ctx.session.execute(
        delete(TradePolicyRow).where(
            TradePolicyRow.issuer_node_id == league_id, TradePolicyRow.kind == TradePolicyKind.SANCTION, TradePolicyRow.partner_node_id == target
        )
    )


async def expel(ctx: TickContext, league: EntityRow, member: LeagueMemberRow, why: str, tally: LeagueTally) -> None:
    if "standing" in (member.locked or []):
        return
    member.standing, member.veto = LeagueStanding.EXPELLED, False
    tally.expelled += 1
    await record(ctx, "league.expelled", roles={IncidentRole.ACTOR: league.id, IncidentRole.VICTIM: member.polity_entity_id}, facts={"why": why})


async def rule_on(ctx: TickContext, league: EntityRow, decision: LeagueDecisionRow, tally: LeagueTally) -> None:
    law = await ctx.session.get(EntityRow, decision.subject_node_id) if decision.subject_node_id is not None else None
    if law is None or law.entity_type is not EntityType.LAW or law.status is not EntityStatus.CANON or held(law.id):
        return
    holder = await realm_of(ctx, law.location_id)
    member = await membership(ctx.session, league.id, holder) if holder is not None else None
    obeyed = member is not None and await obeys(ctx, league, member, f"ruling.{decision.id}")
    if obeyed or ctx.rng(f"leagues.court.{decision.id}").chance(ctx.rules.leagues.court_binding_pct):
        await repeal(ctx, law, f"the court of {league.name} ruled against it")
    tally.rulings += 1
    await record(
        ctx,
        "league.ruling",
        roles={IncidentRole.JUDGE: league.id, IncidentRole.SUBJECT: law.id},
        facts={"outcome": "the law was struck down" if law.status is not EntityStatus.CANON else "the realm kept its law"},
    )


async def call_to_arms(ctx: TickContext, league: EntityRow, enemy: int, tally: LeagueTally) -> None:
    for member in await voters_of(ctx.session, league.id):
        core = await core_of(ctx.session, member.polity_entity_id)
        if core is None or core == enemy or held(core) or not await obeys(ctx, league, member, f"force.{enemy}"):
            continue
        if await declare_war(ctx, core, enemy, f"{definite(league.name)} called its members to arms", world_cap=False):
            tally.calls += 1


async def mediate(ctx: TickContext, league: EntityRow, subject: int) -> None:
    core = await core_of(ctx.session, subject)
    if core is None:
        return
    for member in await voters_of(ctx.session, league.id):
        other = await core_of(ctx.session, member.polity_entity_id)
        if other is not None and other != core:
            await make_peace(ctx, core, other, f"{league.name} brought them to terms")


async def carry(ctx: TickContext, profile: PolityLeagueRow, decision: LeagueDecisionRow, tally: LeagueTally) -> None:
    league = await ctx.session.get(EntityRow, profile.league_entity_id)
    if league is None:
        return
    subject = decision.subject_node_id
    if decision.kind is LeagueDecisionKind.ADMIT:
        polity = await living_polity(ctx.session, subject)
        if polity is not None and not held(polity.id):
            await join(ctx, league, polity, LeagueStanding.MEMBER)
            tally.joined += 1
            await record(
                ctx, "league.joined", roles={IncidentRole.SUBJECT: polity.id, IncidentRole.ACTOR: league.id}, facts={"standing": LeagueStanding.MEMBER}
            )
    elif decision.kind is LeagueDecisionKind.EXPEL and subject is not None:
        member = await membership(ctx.session, league.id, subject)
        if member is not None:
            await expel(ctx, league, member, "the league voted it out", tally)
    elif decision.kind is LeagueDecisionKind.SANCTION and subject is not None:
        await sanction(ctx, league, subject, tally)
    elif decision.kind is LeagueDecisionKind.COMMON_TARIFF and "common_tariff_pct" not in (profile.locked or []):
        profile.common_tariff_pct = decision.rate_pct
    elif decision.kind is LeagueDecisionKind.COMMON_FORCE and subject is not None:
        await call_to_arms(ctx, league, subject, tally)
    elif decision.kind is LeagueDecisionKind.RULING:
        await rule_on(ctx, league, decision, tally)
    elif decision.kind is LeagueDecisionKind.BUDGET and "depth" not in (profile.locked or []):
        spent = min(held_coin(profile.treasury), decision.rate_pct * max(1, profile.treasury) // PERCENT)
        profile.treasury -= spent
        profile.depth = clamp_int(profile.depth + ctx.rules.leagues.depth_gain, 0, PERCENT)
    elif decision.kind is LeagueDecisionKind.MEDIATION and subject is not None:
        await mediate(ctx, league, subject)


async def pending(ctx: TickContext, league_id: int) -> list[LeagueDecisionRow]:
    query = select(LeagueDecisionRow).where(LeagueDecisionRow.league_entity_id == league_id, LeagueDecisionRow.outcome == LeagueDecisionOutcome.PENDING)
    return list(await ctx.session.scalars(query.order_by(LeagueDecisionRow.id)))
