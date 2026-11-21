from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, TreatyPartyRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.leagues import LeagueAim, LeagueDecisionKind, LeagueDecisionOutcome, LeagueOrgan, LeagueStanding, LeagueVoteBasis
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, TreatyKind
from aerona.domain.models.entity_stats import PolityStats, TreatyStats
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, members_of, unions_of
from aerona.engine.leagues.decisions import carry, propose, vote
from aerona.engine.leagues.federation import federate, federating
from aerona.engine.leagues.founding import found_league
from aerona.engine.leagues.rise import apply_legacy
from aerona.engine.leagues.tend import tend_league
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def realm(session: AsyncSession, world: CoreWorld, name: str, *, treasury: int = 1000) -> EntityRow:
    town = await settlement(session, f"{name} Town", world, world.regions[0], population=3000)
    polity = await entity(session, name, EntityType.POLITY, PolityStats(legitimacy=50, stability=50, subjects=1000), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=town.id,
            capital_entity_id=town.id,
            treasury=treasury,
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


async def three(session: AsyncSession, world: CoreWorld) -> list[EntityRow]:
    return [await realm(session, world, name) for name in ("Avel", "Brann", "Coris")]


async def test_realms_found_a_league_with_organs_by_its_aims_and_members_pay_dues(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    tally = LeagueTally()
    league = await found_league(ctx, realms, [LeagueAim.DEFENCE, LeagueAim.LAW], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, tally)
    profile = await session.get(PolityLeagueRow, league.id)
    assert league.entity_type is EntityType.LEAGUE and profile is not None and tally.founded == 1
    assert set(profile.organs) == {LeagueOrgan.ASSEMBLY.value, LeagueOrgan.FORCE.value, LeagueOrgan.COURT.value}
    assert [member.standing for member in await members_of(session, league.id)] == [LeagueStanding.FOUNDER] * 3
    await tend_league(ctx, league, profile, tally)
    assert profile.treasury == 3 * 1000 * profile.dues_pct // 100


async def test_a_veto_blocks_what_the_rest_would_pass(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "veto", tuned_rules(leagues={"obedience_base_pct": 100}))
    realms = await three(session, world)
    outsider = await realm(session, world, "Dorn")
    league = await found_league(ctx, realms, [LeagueAim.PEACE], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    profile = await session.get(PolityLeagueRow, league.id)
    assert profile is not None
    decision = await propose(ctx, profile, LeagueDecisionKind.ADMIT, LeagueOrgan.ASSEMBLY, subject=outsider.id, proposer=realms[0].id)
    assert decision is not None and await vote(ctx, profile, decision, LeagueTally()) is LeagueDecisionOutcome.PASSED
    member = await session.scalar(select(LeagueMemberRow).where(LeagueMemberRow.polity_entity_id == outsider.id))
    assert member is not None and member.standing is LeagueStanding.MEMBER
    expel = await propose(ctx, profile, LeagueDecisionKind.EXPEL, LeagueOrgan.ASSEMBLY, subject=realms[1].id, proposer=realms[0].id)
    assert expel is not None
    holder = await session.scalar(select(LeagueMemberRow).where(LeagueMemberRow.polity_entity_id == realms[2].id))
    assert holder is not None
    holder.veto = True
    ctx_no = await manual_context(session, "veto_no", tuned_rules(leagues={"obedience_base_pct": 0}))
    assert await vote(ctx_no, profile, expel, LeagueTally()) is LeagueDecisionOutcome.VETOED


async def test_a_sanction_lays_a_duty_and_a_customs_union_trades_freely_inside(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    league = await found_league(ctx, realms, [LeagueAim.CUSTOMS_UNION], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    unions, tariffs = await unions_of(session)
    assert unions[realms[0].id] == {league.id} and tariffs[league.id] == ctx.rules.leagues.common_tariff_pct
    profile = await session.get(PolityLeagueRow, league.id)
    assert profile is not None
    decision = await propose(ctx, profile, LeagueDecisionKind.SANCTION, LeagueOrgan.ASSEMBLY, subject=realms[2].id, proposer=realms[0].id)
    assert decision is not None
    decision.outcome = LeagueDecisionOutcome.PENDING
    await carry(ctx, profile, decision, LeagueTally())
    row = await session.scalar(select(TradePolicyRow).where(TradePolicyRow.issuer_node_id == league.id))
    assert row is not None and row.kind is TradePolicyKind.SANCTION and row.partner_node_id == realms[2].id


async def test_the_court_strikes_down_a_members_law(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "court", tuned_rules(leagues={"obedience_base_pct": 100, "court_binding_pct": 100}))
    realms = await three(session, world)
    league = await found_league(ctx, realms, [LeagueAim.LAW], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    profile = await session.get(PolityLeagueRow, league.id)
    assert profile is not None
    law = await enact(ctx, realms[1], LawKind.COMPETITION_LAW, {})
    decision = await propose(ctx, profile, LeagueDecisionKind.RULING, LeagueOrgan.COURT, subject=law.id, proposer=realms[0].id)
    assert decision is not None
    await vote(ctx, profile, decision, LeagueTally())
    assert law.status is not EntityStatus.CANON
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "league.ruling")) is not None


async def test_an_attack_on_one_member_brings_a_call_to_arms_before_the_force(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    league = await found_league(ctx, realms, [LeagueAim.DEFENCE], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    profile = await session.get(PolityLeagueRow, league.id)
    first = await session.get(PolityProfileRow, realms[0].id)
    assert profile is not None and first is not None and first.core_entity_id is not None
    foe = await settlement(session, "Foehold", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(first.core_entity_id, foe.id, BondKind.ENEMY, ctx.epoch, "at war"))
    await tend_league(ctx, league, profile, LeagueTally())
    decision = await session.scalar(select(LeagueDecisionRow).where(LeagueDecisionRow.kind == LeagueDecisionKind.COMMON_FORCE))
    assert decision is not None and decision.subject_node_id == foe.id and decision.organ is LeagueOrgan.FORCE


async def test_a_league_left_with_too_few_realms_dissolves(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    league = await found_league(ctx, realms, [LeagueAim.TRADE], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    profile = await session.get(PolityLeagueRow, league.id)
    assert profile is not None
    realms[2].status, realms[2].end_epoch = EntityStatus.DEAD, ctx.epoch
    tally = LeagueTally()
    await tend_league(ctx, league, profile, tally)
    assert tally.dissolved == 1 and league.status is not EntityStatus.CANON


async def test_a_deep_league_for_defence_and_trade_becomes_one_federation(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    league = await found_league(ctx, realms, [LeagueAim.DEFENCE, LeagueAim.TRADE], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, LeagueTally())
    profile = await session.get(PolityLeagueRow, league.id)
    assert profile is not None
    profile.depth = ctx.rules.leagues.federate_depth_threshold
    assert federating(profile, ctx.rules.leagues.federate_depth_threshold)
    tally = LeagueTally()
    union = await federate(ctx, league, profile, await members_of(session, league.id), tally)
    assert union is not None and tally.federated == 1
    federation = await session.get(PolityProfileRow, union.id)
    assert federation is not None and federation.government is GovernmentKind.FEDERATION
    towns = set(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == union.id)))
    assert len(towns) == 3 and all(polity.status is not EntityStatus.CANON for polity in realms)


async def test_a_coalition_of_three_becomes_a_league_with_its_treaty_as_charter(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realms = await three(session, world)
    treaty = await entity(session, "The Coalition", EntityType.TREATY, TreatyStats(), world_id=world.world.id)
    session.add(TreatyProfileRow(treaty_entity_id=treaty.id, kind=TreatyKind.COALITION, signed_epoch=0))
    session.add_all([TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=polity.id) for polity in realms])
    await session.flush()
    tally = LeagueTally()
    await apply_legacy(ctx, tally)
    profile = await session.scalar(select(PolityLeagueRow))
    assert tally.founded == 1 and profile is not None and profile.charter_treaty_id == treaty.id
