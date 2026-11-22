from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, MovementCause
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, OfficeKind
from aerona.domain.enums.referendums import ReferendumCaller, ReferendumResult, ReferendumSubject
from aerona.domain.models.entity_stats import FactionStats, IdeologyStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.referendums.book import ReferendumTally
from aerona.engine.referendums.voting import assembly_questions, call_vote, hold, petitions
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def voting_realm(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow, EntityRow]:
    capital = await settlement(session, "Votehold", world, world.regions[0], population=4000)
    other = await settlement(session, "Farvote", world, world.regions[0], population=2000)
    realm = await entity(session, "The Voting Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id,
            government=next(iter(GovernmentKind)),
            decision_rule=DecisionRule.ASSEMBLY,
            core_entity_id=capital.id,
            capital_entity_id=capital.id,
            legitimacy=60,
        )
    )
    session.add_all(
        [PolityMemberRow(polity_entity_id=realm.id, member_entity_id=capital.id), PolityMemberRow(polity_entity_id=realm.id, member_entity_id=other.id)]
    )
    await session.flush()
    return realm, capital, other


async def asked(ctx: TickContext, realm: EntityRow, subject: ReferendumSubject, target: int | None, *, binding: bool = True) -> ReferendumRow:
    return await call_vote(ctx, realm, subject, target, binding=binding, caller=ReferendumCaller.RULER, called_by=None, tally=ReferendumTally())


async def test_a_binding_vote_for_independence_frees_the_town(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, _capital, other = await voting_realm(session, world)
    row = await asked(ctx, realm, ReferendumSubject.INDEPENDENCE, other.id)
    row.yes_pct = 80
    tally = ReferendumTally()
    await hold(ctx, row, tally)
    assert row.result is ReferendumResult.PASSED and tally.carried == 1
    assert (
        await session.scalar(select(PolityMemberRow).where(PolityMemberRow.polity_entity_id == realm.id, PolityMemberRow.member_entity_id == other.id)) is None
    )
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "vote.result")) is not None


async def test_a_vote_that_does_not_bind_is_ignored_at_a_cost_in_legitimacy(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ignore", tuned_rules(referendums={"obey_chance_pct": 0}))
    realm, _capital, other = await voting_realm(session, world)
    row = await asked(ctx, realm, ReferendumSubject.INDEPENDENCE, other.id, binding=False)
    row.yes_pct = 90
    await hold(ctx, row, ReferendumTally())
    profile = await session.get(PolityProfileRow, realm.id)
    assert row.ignored and profile is not None and profile.legitimacy == 60 - ctx.rules.referendums.ignore_legitimacy_loss


async def test_a_vote_bent_by_fraud_is_found_out_and_counts_for_nothing(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fraud", tuned_rules(referendums={"fraud_detect_pct": 100}))
    realm, _capital, other = await voting_realm(session, world)
    row = await asked(ctx, realm, ReferendumSubject.INDEPENDENCE, other.id)
    row.fraud, row.yes_pct = 100, 95
    await hold(ctx, row, ReferendumTally())
    assert row.result is ReferendumResult.VOID
    assert await session.scalar(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == other.id)) is not None


async def test_a_law_voted_down_is_repealed_and_a_recall_empties_the_office(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, capital, _other = await voting_realm(session, world)
    law = await enact(ctx, realm, LawKind.COMPETITION_LAW, {})
    vote = await asked(ctx, realm, ReferendumSubject.LAW, law.id)
    vote.yes_pct = 10
    await hold(ctx, vote, ReferendumTally())
    assert vote.result is ReferendumResult.FAILED and law.status is not EntityStatus.CANON
    officer = await mortal(session, "Cass Dunmore", world, capital.id)
    office = OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.TREASURER, holder_entity_id=officer.id, since_epoch=0, powers=[])
    session.add(office)
    await session.flush()
    recall = await asked(ctx, realm, ReferendumSubject.RECALL, officer.id)
    recall.yes_pct = 70
    await hold(ctx, recall, ReferendumTally())
    assert office.holder_entity_id is None


async def test_a_faith_voted_in_becomes_the_faith_of_the_realm(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, _capital, _other = await voting_realm(session, world)
    faith = await entity(session, "The Open Way", EntityType.IDEOLOGY, IdeologyStats(), world_id=world.world.id)
    row = await asked(ctx, realm, ReferendumSubject.FAITH, faith.id)
    row.yes_pct = 75
    await hold(ctx, row, ReferendumTally())
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None and profile.state_religion_id == faith.id


async def test_a_movement_for_independence_with_support_petitions_a_vote(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, _capital, other = await voting_realm(session, world)
    cause = await entity(session, "The Free Far", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(FactionProfileRow(faction_entity_id=cause.id, kind=FactionKind.MOVEMENT, influence_over={}, cohort_share={}, locked=[]))
    session.add(
        MovementProfileRow(
            faction_entity_id=cause.id, cause=MovementCause.INDEPENDENCE, polity_entity_id=realm.id, target_entity_id=other.id, support=50, locked=[]
        )
    )
    await session.flush()
    tally = ReferendumTally()
    await petitions(ctx, tally)
    row = await session.scalar(select(ReferendumRow))
    assert tally.called == 1 and row is not None and row.caller is ReferendumCaller.PETITION and not row.binding and row.target_node_id == other.id
    await petitions(ctx, tally)
    assert tally.called == 1


async def test_an_assembly_puts_its_newest_law_to_the_people_and_never_the_same_law_twice(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "assembly", tuned_rules(referendums={"assembly_call_pct": 100}))
    realm, _capital, _other = await voting_realm(session, world)
    law = await enact(ctx, realm, LawKind.TAX_RATE, {})
    tally = ReferendumTally()
    await assembly_questions(ctx, tally)
    row = await session.scalar(select(ReferendumRow).where(ReferendumRow.holder_node_id == realm.id))
    assert row is not None and row.subject is ReferendumSubject.LAW and row.target_node_id == law.id and row.caller is ReferendumCaller.ASSEMBLY
    await assembly_questions(ctx, ReferendumTally())
    rows = list(await session.scalars(select(ReferendumRow).where(ReferendumRow.holder_node_id == realm.id)))
    assert len(rows) == 1
