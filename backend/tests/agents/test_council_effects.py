from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.scope import load_scope
from aerona.agents.council import agenda, apply_council
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.session import Database
from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.agent import CouncilCaller, CouncilVote
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import SonDeathCause
from aerona.domain.enums.war import WarStatus
from aerona.engine.gods.god_death import god_death
from aerona.engine.services.war import open_war
from aerona.prompts.schemas.council import CouncilDecision, CouncilOutput, VoteOutput
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, make_context, make_entity, make_son, seed_gods_world


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def gods(session: AsyncSession) -> GodsWorld:
    return await seed_gods_world(session)


def _output(votes: list[VoteOutput], decision: CouncilDecision = CouncilDecision.NONE) -> CouncilOutput:
    return CouncilOutput(speeches=[], motion="The motion.", votes=votes, alliances=[], decision=decision, minutes="They met.", agenda="the course of the world")


def _vote(son_id: int, vote: CouncilVote) -> VoteOutput:
    return VoteOutput(son_id=son_id, vote=vote, reason="Because.")


async def test_agenda_follows_the_priority_order(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    scope = await load_scope(session, rules)
    assert "which brother has grown too great" in await agenda(scope)
    thread = ThreadRow(epoch=1, text="The drowned bell still rings")
    session.add(thread)
    await session.flush()
    assert "Unresolved story: The drowned bell still rings" in await agenda(scope)
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=gods.world.id, location_id=gods.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=gods.world.id, location_id=gods.region.id)
    war = await open_war(make_context(session, rules, 2), first, second)
    war.status = WarStatus.ONGOING
    await session.flush()
    assert "will the gods take sides in the mortals' war" in await agenda(scope)
    dead = await make_son(session, "Velkar", gods.world.id)
    await god_death(make_context(session, rules, 2), dead, "fell", SonDeathCause.OTHER)
    assert "The dead brother Velkar" in await agenda(scope)
    rebel = await make_son(session, "Iolen", gods.world.id)
    rebel.rebel = True
    await session.flush()
    assert "Iolen's rebellion against the father" in await agenda(scope)
    gods.cosmos.doom_clock = rules.balance.apocalypse_threshold
    assert f"Doomsday clock {rules.balance.apocalypse_threshold}/" in await agenda(scope)


async def test_a_stale_death_does_not_set_the_agenda(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    dead = await make_son(session, "Velkar", gods.world.id)
    await god_death(make_context(session, rules, 1), dead, "fell", SonDeathCause.OTHER)
    gods.cosmos.epoch = 5
    scope = await load_scope(session, rules)
    assert "The dead brother" not in await agenda(scope)


async def test_same_votes_bring_sons_closer_and_opposite_votes_push_apart(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    first = await make_son(session, "Velkar", gods.world.id)
    second = await make_son(session, "Iolen", gods.world.id)
    third = await make_son(session, "Brann", gods.world.id)
    fourth = await make_son(session, "Sael", gods.world.id)
    scope = await load_scope(session, rules)
    output = _output(
        [_vote(first.id, CouncilVote.YES), _vote(second.id, CouncilVote.YES), _vote(third.id, CouncilVote.NO), _vote(fourth.id, CouncilVote.ABSTAIN)]
    )
    await apply_council(scope, [first, second, third, fourth], output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    relations = SonRepository(session)
    closeness = rules.council.same_vote_closeness
    assert await relations.relation(first.id, second.id) == closeness
    assert await relations.relation(first.id, third.id) == -closeness
    assert await relations.relation(second.id, third.id) == -closeness
    assert await relations.relation(first.id, fourth.id) == 0
    assert await relations.relation(third.id, fourth.id) == 0


async def test_a_passed_anti_doomsday_motion_pushes_the_clock_back(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    sons = [await make_son(session, name, gods.world.id) for name in ("Velkar", "Iolen")]
    gods.cosmos.doom_clock = 80
    scope = await load_scope(session, rules)
    output = _output([_vote(son.id, CouncilVote.YES) for son in sons], CouncilDecision.AGAINST_DOOMSDAY)
    result = await apply_council(scope, sons, output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    assert result.passed
    assert gods.cosmos.doom_clock == 80 - rules.council.apocalypse_motion_push


async def test_a_rejected_motion_changes_nothing(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    sons = [await make_son(session, name, gods.world.id) for name in ("Velkar", "Iolen")]
    gods.cosmos.doom_clock = 80
    scope = await load_scope(session, rules)
    output = _output([_vote(son.id, CouncilVote.NO) for son in sons], CouncilDecision.AGAINST_DOOMSDAY)
    result = await apply_council(scope, sons, output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    assert not result.passed and gods.cosmos.doom_clock == 80


async def test_a_passed_censure_lowers_the_fame_of_rebels_only(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    rebel = await make_son(session, "Velkar", gods.world.id)
    loyal = await make_son(session, "Iolen", gods.world.id)
    rebel.rebel = True
    rebel.fame = 50
    loyal.fame = 50
    scope = await load_scope(session, rules)
    output = _output([_vote(rebel.id, CouncilVote.YES), _vote(loyal.id, CouncilVote.YES)], CouncilDecision.CONDEMN_REBEL)
    result = await apply_council(scope, [rebel, loyal], output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    assert result.passed
    assert rebel.fame == 50 - rules.council.censure_renown_cost
    assert loyal.fame == 50


async def test_a_passed_peace_call_closes_the_most_important_enmity(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    sons = [await make_son(session, name, gods.world.id) for name in ("Velkar", "Iolen")]
    small_a = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=gods.world.id, location_id=gods.region.id)
    small_b = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=gods.world.id, location_id=gods.region.id)
    big_a = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=gods.world.id)
    big_b = await make_entity(session, "Saltfolk", EntityType.PEOPLE, world_id=gods.world.id)
    bonds = BondRepository(session)
    for first, second in ((small_a, small_b), (big_a, big_b)):
        await bonds.connect(BondDraft(first.id, second.id, BondKind.ENEMY, 1))
    scope = await load_scope(session, rules)
    output = _output([_vote(son.id, CouncilVote.YES) for son in sons], CouncilDecision.CALL_FOR_PEACE)
    result = await apply_council(scope, sons, output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    assert any("made peace" in note for note in result.notes)
    assert not await bonds.exists_between(big_a.id, big_b.id, BondKind.ENEMY)
    assert await bonds.exists_between(small_a.id, small_b.id, BondKind.ENEMY)


async def test_a_peace_call_without_enmity_adds_no_note(session: AsyncSession, gods: GodsWorld, rules: Rules) -> None:
    sons = [await make_son(session, name, gods.world.id) for name in ("Velkar", "Iolen")]
    scope = await load_scope(session, rules)
    output = _output([_vote(son.id, CouncilVote.YES) for son in sons], CouncilDecision.CALL_FOR_PEACE)
    result = await apply_council(scope, sons, output, "topic", caller=CouncilCaller.FATE, god_asked=False)
    assert result.passed and result.notes == []
