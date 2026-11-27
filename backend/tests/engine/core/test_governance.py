from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow, CompanyShareRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgCliqueRow, OrgGovernanceRow, OrgMergerRow, OrgResearchRow, OrgSeatRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.governance import (
    CliqueAim,
    GoverningBody,
    HeadSelection,
    InsolvencyPath,
    InsolvencyStage,
    MergerKind,
    MergerStage,
    OrgStrategy,
    VoteBasis,
)
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.governance.cliques import tend_cliques
from aerona.engine.governance.heads import govern
from aerona.engine.governance.insolvency import InsolvencyTally, advance_case, file_case
from aerona.engine.governance.mergers import advance_merger, open_bid
from aerona.engine.governance.research import advance_research, begin_research, spread_secrets
from aerona.engine.governance.seats import LEGACY_FIXUP, seed_governance, sync_seats
from aerona.engine.governance.strategy import courses_open, set_course
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def organisation(session: AsyncSession, world: CoreWorld, name: str, kind: FactionKind, members: list[EntityRow], *, treasury: int = 400) -> EntityRow:
    org = await entity(
        session, name, EntityType.FACTION, FactionStats(strength=40, wealth=40, sway=30), world_id=world.world.id, location_id=world.regions[0].id
    )
    session.add(
        FactionProfileRow(
            faction_entity_id=org.id,
            kind=kind,
            treasury=treasury,
            influence_over={},
            cohort_share={},
            leader_entity_id=members[0].id if members else None,
            locked=[],
        )
    )
    for index, member in enumerate(members):
        rank = FactionRank.LEADER if index == 0 else FactionRank.OFFICER if index < 3 else FactionRank.MEMBER
        session.add(FactionMembershipRow(faction_entity_id=org.id, mortal_entity_id=member.id, rank=rank, joined_epoch=index, locked=[]))
    await session.flush()
    return org


async def folk(session: AsyncSession, world: CoreWorld, count: int, prefix: str = "Member") -> list[EntityRow]:
    town = await settlement(session, f"{prefix} Town", world, world.regions[0])
    return [await mortal(session, f"{prefix} {index}", world, town.id, charisma=30 + index * 5, intellect=40, wisdom=30 + index) for index in range(count)]


async def body_of(session: AsyncSession, org: EntityRow) -> OrgGovernanceRow:
    row = await session.get(OrgGovernanceRow, org.id)
    assert row is not None
    return row


async def test_companies_gain_a_shareholders_meeting_and_older_factions_a_head_body_with_whole_votes(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    people = await folk(session, world, 4)
    guild = await organisation(session, world, "The Lamp Guild", FactionKind.CRAFT_GUILD, people)
    company = await organisation(session, world, "The Far Company", FactionKind.CHARTERED_COMPANY, people[:1])
    session.add(CompanyProfileRow(faction_entity_id=company.id, value=40, locked=[]))
    session.add_all(
        [
            CompanyShareRow(company_entity_id=company.id, holder_node_id=people[1].id, share=60, locked=False),
            CompanyShareRow(company_entity_id=company.id, holder_node_id=people[2].id, share=40, locked=False),
        ]
    )
    await session.flush()
    tally = await seed_governance(ctx)
    assert tally.bodies == 2
    guild_body, company_body = await body_of(session, guild), await body_of(session, company)
    assert guild_body.decision_body is GoverningBody.HEAD and guild_body.head_node_id == people[0].id
    assert guild_body.head_selection is HeadSelection.ELECTED_BY_MEMBERS
    assert company_body.decision_body is GoverningBody.SHAREHOLDERS_MEETING and company_body.vote_basis is VoteBasis.BY_SHARE
    await sync_seats(ctx, company_body)
    seats = {seat.member_node_id: seat.vote_weight for seat in await session.scalars(select(OrgSeatRow).where(OrgSeatRow.org_node_id == company.id))}
    assert seats == {people[1].id: 60, people[2].id: 40}
    newcomer = await organisation(session, world, "The New Hall", FactionKind.CRAFT_GUILD, people)
    await seed_governance(ctx)
    assert (await body_of(session, newcomer)).decision_body is GoverningBody.ASSEMBLY_OF_MEMBERS
    assert await session.get(AppliedFixupRow, LEGACY_FIXUP) is not None


async def test_a_body_elects_the_candidate_its_clique_backs_when_the_term_ends(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    people = await folk(session, world, 5)
    guild = await organisation(session, world, "The Weigh House", FactionKind.MERCHANT_GUILD, people)
    await seed_governance(ctx)
    body = await body_of(session, guild)
    body.decision_body, body.head_selection, body.vote_basis, body.term_ends_epoch = (
        GoverningBody.ASSEMBLY_OF_MEMBERS,
        HeadSelection.ELECTED_BY_BODY,
        VoteBasis.ONE_MEMBER_ONE_VOTE,
        ctx.epoch,
    )
    await sync_seats(ctx, body)
    backers = [person.id for person in people[1:]]
    session.add(OrgCliqueRow(org_node_id=guild.id, name="those around the fourth", members=backers, aim=CliqueAim.HEAD, aim_node_id=people[3].id, locked=[]))
    await session.flush()
    chosen, _defied, _removed = await govern(ctx, body)
    profile = await session.get(FactionProfileRow, guild.id)
    assert chosen and body.head_node_id == people[3].id and profile is not None and profile.leader_entity_id == people[3].id
    assert body.term_ends_epoch == ctx.epoch + body.term_epochs


async def test_a_course_passes_with_its_quorum_a_defiant_head_loses_trust_and_is_removed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "votes", tuned_rules(governance={"head_defiance_trust_loss": 40, "removal_trust": 30}))
    people = await folk(session, world, 4)
    guild = await organisation(session, world, "The Seal House", FactionKind.CRAFT_GUILD, people)
    await seed_governance(ctx)
    body = await body_of(session, guild)
    body.decision_body, body.vote_basis, body.term_ends_epoch = GoverningBody.ASSEMBLY_OF_MEMBERS, VoteBasis.ONE_MEMBER_ONE_VOTE, ctx.epoch + 5
    await sync_seats(ctx, body)
    session.add(
        OrgCliqueRow(
            org_node_id=guild.id,
            name="the growers",
            members=[person.id for person in people[1:]],
            aim=CliqueAim.STRATEGY,
            aim_strategy=OrgStrategy.GROW,
            locked=[],
        )
    )
    await session.flush()
    await govern(ctx, body)
    assert body.strategy is OrgStrategy.GROW
    session.add(
        OrgCliqueRow(org_node_id=guild.id, name="the head's own", members=[people[0].id], aim=CliqueAim.STRATEGY, aim_strategy=OrgStrategy.HOLD, locked=[])
    )
    body.strategy = OrgStrategy.HOLD
    await session.flush()
    _chosen, defied, removed = await govern(ctx, body)
    assert defied and removed and body.head_node_id not in (None, people[0].id) and body.trust == ctx.rules.governance.new_head_trust


async def test_a_strong_clique_splits_away_with_its_members_and_its_share(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "split", tuned_rules(governance={"split_clique_threshold": 30, "clique_form_chance_pct": 0}))
    people = await folk(session, world, 6)
    guild = await organisation(session, world, "The Old Order", FactionKind.HOLY_ORDER, people, treasury=1000)
    await seed_governance(ctx)
    body = await body_of(session, guild)
    body.decision_body, body.vote_basis = GoverningBody.ASSEMBLY_OF_MEMBERS, VoteBasis.ONE_MEMBER_ONE_VOTE
    await sync_seats(ctx, body)
    leaving = [person.id for person in people[3:]]
    session.add(OrgCliqueRow(org_node_id=guild.id, name="the leavers", leader_node_id=people[3].id, members=leaving, aim=CliqueAim.SPLIT, locked=[]))
    await session.flush()
    _formed, split = await tend_cliques(ctx, body)
    assert split == 1
    child = await session.scalar(select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == people[3].id))
    assert child is not None and child != guild.id
    parent, offshoot = await session.get(FactionProfileRow, guild.id), await session.get(FactionProfileRow, child)
    assert parent is not None and offshoot is not None and offshoot.treasury > 0 and parent.treasury + offshoot.treasury == 1000


async def test_a_clique_led_by_the_head_never_splits_from_its_own_body(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "split.head", tuned_rules(governance={"split_clique_threshold": 30, "clique_form_chance_pct": 0}))
    people = await folk(session, world, 6)
    guild = await organisation(session, world, "The Kept Order", FactionKind.HOLY_ORDER, people, treasury=1000)
    await seed_governance(ctx)
    body = await body_of(session, guild)
    body.decision_body, body.vote_basis = GoverningBody.ASSEMBLY_OF_MEMBERS, VoteBasis.ONE_MEMBER_ONE_VOTE
    body.head_node_id = people[0].id
    await sync_seats(ctx, body)
    members = [people[0].id, *(person.id for person in people[3:])]
    session.add(OrgCliqueRow(org_node_id=guild.id, name="those around the head", leader_node_id=people[0].id, members=members, aim=CliqueAim.SPLIT, locked=[]))
    await session.flush()
    _formed, split = await tend_cliques(ctx, body)
    assert split == 0


async def test_a_friendly_merger_joins_members_and_debts_and_pays_the_owners(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    people = await folk(session, world, 4)
    acquirer = await organisation(session, world, "The Great House", FactionKind.MERCHANT_GUILD, people[:2], treasury=500)
    target = await organisation(session, world, "The Small House", FactionKind.MERCHANT_GUILD, people[2:], treasury=50)
    set_stats(acquirer, wealth=90)
    set_stats(target, wealth=2)
    lender = await organisation(session, world, "The Lenders", FactionKind.FINANCIERS, [], treasury=10)
    loan = LoanRow(
        lender_entity_id=lender.id,
        borrower_entity_id=target.id,
        principal=40,
        interest_pct=5,
        issued_epoch=0,
        due_epoch=9,
        status=LoanStatus.OPEN,
        purpose="stock",
    )
    session.add(loan)
    await session.flush()
    merger = await open_bid(ctx, acquirer.id, target, MergerKind.FRIENDLY_ACQUISITION, None)
    assert await advance_merger(ctx, merger) == "agreed"
    assert await advance_merger(ctx, merger) == "closed"
    assert merger.stage is MergerStage.CLOSED and target.status is not EntityStatus.CANON
    moved = await session.scalar(select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == people[2].id))
    assert moved == acquirer.id and loan.borrower_entity_id == acquirer.id


async def test_a_hostile_bid_meets_resistance_and_turns_to_a_friendly_buyer(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    people = await folk(session, world, 3)
    raider = await organisation(session, world, "The Raiders", FactionKind.MERCHANT_GUILD, people[:1], treasury=900)
    target = await organisation(session, world, "The Quiet House", FactionKind.CRAFT_GUILD, people[1:2], treasury=40)
    friend = await organisation(session, world, "The Friendly House", FactionKind.CRAFT_GUILD, people[2:], treasury=900)
    for org, wealth in ((raider, 90), (target, 5), (friend, 90)):
        set_stats(org, wealth=wealth)
    await seed_governance(ctx)
    (await body_of(session, target)).trust = 100
    merger = await open_bid(ctx, raider.id, target, MergerKind.HOSTILE_TAKEOVER, None)
    assert await advance_merger(ctx, merger) == "resisted"
    assert merger.friendly_buyer_node_id == friend.id
    await advance_merger(ctx, merger)
    assert merger.stage is MergerStage.WITHDRAWN
    friendly = await session.scalar(select(OrgMergerRow).where(OrgMergerRow.acquirer_node_id == friend.id))
    assert friendly is not None and friendly.kind is MergerKind.FRIENDLY_ACQUISITION


async def test_research_spends_its_budget_gives_a_secret_technique_and_leaks_in_time(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "research", tuned_rules(governance={"research_progress_per_staff": 50, "secret_spread_per_epoch_pct": 100}))
    people = await folk(session, world, 2)
    academy = await organisation(session, world, "The Academy", FactionKind.SCHOLARS_ACADEMY, people, treasury=2000)
    set_stats(academy, wealth=90)
    technique = next(iter(Technique))
    row = await begin_research(ctx, academy, technique, None, 500)
    row.staff, row.secrecy = 2, 0
    assert await advance_research(ctx, academy, row)
    known = await session.get(HolderTechniqueRow, (academy.id, technique))
    assert row.done_epoch == ctx.epoch and known is not None and row.budget < 500
    known.secret = True
    assert await spread_secrets(ctx, academy) == 1 and not known.secret


async def test_insolvency_runs_to_liquidation_and_restructuring_by_its_path(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    people = await folk(session, world, 2)
    lender = await organisation(session, world, "The Bank", FactionKind.FINANCIERS, [], treasury=10)
    failing = await organisation(session, world, "The Failing House", FactionKind.MERCHANT_GUILD, people[:1], treasury=0)
    bending = await organisation(session, world, "The Bending House", FactionKind.MERCHANT_GUILD, people[1:], treasury=0)
    for debtor in (failing, bending):
        set_stats(debtor, wealth=1)
        session.add(
            LoanRow(
                lender_entity_id=lender.id,
                borrower_entity_id=debtor.id,
                principal=100,
                interest_pct=5,
                issued_epoch=0,
                due_epoch=1,
                status=LoanStatus.OPEN,
                purpose="ships",
            )
        )
    await session.flush()
    tally = InsolvencyTally()
    wound_up = await file_case(ctx, failing, InsolvencyPath.LIQUIDATION, tally)
    restructured = await file_case(ctx, bending, InsolvencyPath.RESTRUCTURING, tally)
    assert wound_up is not None and restructured is not None and wound_up.creditors == [lender.id] and wound_up.owed == 100
    for _stage in range(3):
        await advance_case(ctx, wound_up, tally)
        await advance_case(ctx, restructured, tally)
    assert wound_up.stage is InsolvencyStage.CLOSED and failing.status is not EntityStatus.CANON and tally.liquidated == 1
    assert restructured.stage is InsolvencyStage.CLOSED and bending.status is EntityStatus.CANON and tally.restructured == 1
    loan = await session.scalar(select(LoanRow).where(LoanRow.borrower_entity_id == bending.id))
    assert loan is not None and loan.principal <= 100 and wound_up.recovered_pct >= ctx.rules.governance.creditor_recovery_floor_pct
    assert await session.scalar(select(InsolvencyCaseRow.id).where(InsolvencyCaseRow.debtor_node_id == failing.id)) is not None
    assert await session.scalar(select(OrgResearchRow.id)) is None


async def test_a_head_sets_a_new_course_among_those_its_treasury_allows(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "course", tuned_rules(governance={"course_change_pct": 100}))
    poor = await organisation(session, world, "The Lean Guild", FactionKind.MERCHANT_GUILD, await folk(session, world, 3, "Lean"), treasury=0)
    rich = await organisation(session, world, "The Deep Guild", FactionKind.MERCHANT_GUILD, await folk(session, world, 3, "Deep"), treasury=5000)
    await seed_governance(ctx)
    poor_body, rich_body = await body_of(session, poor), await body_of(session, rich)
    assert poor_body.head_node_id is not None and rich_body.head_node_id is not None
    assert await set_course(ctx, poor_body, poor) and await set_course(ctx, rich_body, rich)
    assert poor_body.strategy is not OrgStrategy.HOLD and poor_body.strategy not in {OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_UP, OrgStrategy.RESEARCH}
    poor_profile = await session.get(FactionProfileRow, poor.id)
    rich_profile = await session.get(FactionProfileRow, rich.id)
    assert poor_profile is not None and rich_profile is not None
    assert OrgStrategy.WITHDRAW in await courses_open(ctx, poor, poor_profile)
    assert OrgStrategy.EXPAND_ABROAD in await courses_open(ctx, rich, rich_profile) and OrgStrategy.WITHDRAW not in await courses_open(ctx, rich, rich_profile)


async def test_a_revolt_or_a_movement_never_takes_a_market_course(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "unmarket", tuned_rules(governance={"course_change_pct": 100}))
    rebels = await organisation(session, world, "The Ash Rising", FactionKind.REBELS, await folk(session, world, 3, "Ash"), treasury=5000)
    guild = await organisation(session, world, "The Salt Guild", FactionKind.MERCHANT_GUILD, await folk(session, world, 3, "Salt"), treasury=5000)
    rebel_profile = await session.get(FactionProfileRow, rebels.id)
    guild_profile = await session.get(FactionProfileRow, guild.id)
    assert rebel_profile is not None and guild_profile is not None
    market = {OrgStrategy.SPECIALISE, OrgStrategy.DIVERSIFY, OrgStrategy.EXPAND_ABROAD, OrgStrategy.INTEGRATE_UP, OrgStrategy.INTEGRATE_DOWN}
    assert not market & set(await courses_open(ctx, rebels, rebel_profile))
    assert market <= set(await courses_open(ctx, guild, guild_profile))
