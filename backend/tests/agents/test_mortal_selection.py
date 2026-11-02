import math
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.scope import load_scope
from aerona.agents.fate.selection import judge_origins, records_to_judge
from aerona.agents.mortal import (
    Candidate,
    MortalTurnResult,
    StartedMortalTurn,
    candidates,
    choose_mortal_agents,
    finish_mortal_turn,
    pick,
    run_mortal_turn,
    score,
)
from aerona.agents.runtime import AgentRuntime
from aerona.agents.turns.session import SessionStatus, TurnOutcome
from aerona.agents.turns.state import begin_turn, finish_turn, save_turn, turn_row
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, MessageRow
from aerona.domain.enums.agent import AgentKind, MessageIntent
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType
from aerona.domain.models.entity_stats import PeopleStats, SettlementStats
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel, spoken
from tests.agents.world import AgentWorld
from tests.engine.core.factories import add_empty_world

EPOCH = 4


def tuned_tools(rules: Rules, **values: int) -> Rules:
    return replace(rules, mortal_tools=replace(rules.mortal_tools, **values))


def die_one(rules: Rules) -> Rules:
    return tuned_tools(rules, agent_random_die=1)


def rng() -> SeededRandom:
    return SeededRandom.for_epoch(1, EPOCH, "test")


async def spawn(
    session: AsyncSession, name: str, entity_type: EntityType, world_id: int, *, power: int = 3, population: int = 1000, birth_epoch: int = 1
) -> EntityRow:
    stats = PeopleStats(population=population) if entity_type is EntityType.PEOPLE else SettlementStats(population=population)
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {entity_type.value} {name}.",
            stats=stats,
            power_level=power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=birth_epoch,
            world_id=world_id,
            split_title=False,
        )
    )


def plain(entity: EntityRow, *, forced: bool = False, chosen: bool = False, dreaming: bool = False) -> Candidate:
    return Candidate(entity, forced, chosen, dreaming)


async def test_score_combines_power_log_crowd_wait_and_die(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = die_one(rules)
    tools = tuned.mortal_tools
    async with database.write() as session:
        entity = await spawn(session, "Scored Folk", EntityType.PEOPLE, world.core.world.id, power=4, population=10000)
        entity.last_acted_epoch = EPOCH - 3
        expected = 4 * tools.agent_power_weight + math.log10(10000) * tools.agent_population_weight + min(tools.agent_wait_cap, 3 * tools.agent_wait_weight) + 1
        assert score(tuned, plain(entity), EPOCH, rng()) == expected


async def test_score_bonuses_for_chosen_and_dreaming_and_wait_cap(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = die_one(rules)
    tools = tuned.mortal_tools
    async with database.write() as session:
        entity = await spawn(session, "Scored Folk", EntityType.PEOPLE, world.core.world.id)
        entity.last_acted_epoch = EPOCH - 1
        base = score(tuned, plain(entity), EPOCH, rng())
        assert score(tuned, plain(entity, chosen=True), EPOCH, rng()) == base + tools.agent_chosen_bonus
        assert score(tuned, plain(entity, dreaming=True), EPOCH, rng()) == base + tools.agent_dream_bonus
        capped = score(tuned, plain(entity), EPOCH + 100, rng())
        assert capped - base == tools.agent_wait_cap - tools.agent_wait_weight


async def test_score_crowd_has_a_floor_and_a_logarithmic_slope(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = die_one(rules)
    async with database.write() as session:
        tiny = await spawn(session, "Tiny", EntityType.PEOPLE, world.core.world.id, population=1)
        small = await spawn(session, "Small", EntityType.PEOPLE, world.core.world.id, population=10)
        huge = await spawn(session, "Huge", EntityType.PEOPLE, world.core.world.id, population=100000)
        for item in (tiny, small, huge):
            item.last_acted_epoch = 0
        assert score(tuned, plain(tiny), EPOCH, rng()) == score(tuned, plain(small), EPOCH, rng())
        gain = score(tuned, plain(huge), EPOCH, rng()) - score(tuned, plain(small), EPOCH, rng())
        assert gain == 4 * tuned.mortal_tools.agent_population_weight


async def test_pick_spreads_the_choice_across_entity_types(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = tuned_tools(rules, agent_random_die=1, agent_type_share_divisor=2)
    async with database.write() as session:
        peoples = [plain(await spawn(session, f"Folk {index}", EntityType.PEOPLE, world.core.world.id, power=9)) for index in range(4)]
        towns = [plain(await spawn(session, f"Town {index}", EntityType.SETTLEMENT, world.core.world.id, power=1)) for index in range(2)]
        chosen = pick(tuned, [*peoples, *towns], 4, EPOCH, rng())
        kinds = [candidate.entity.entity_type for candidate in chosen]
        assert kinds.count(EntityType.PEOPLE) == 2 and kinds.count(EntityType.SETTLEMENT) == 2
        unspread = pick(tuned_tools(rules, agent_random_die=1, agent_type_share_divisor=1), [*peoples, *towns], 4, EPOCH, rng())
        assert all(candidate.entity.entity_type is EntityType.PEOPLE for candidate in unspread)


async def test_pick_backfills_when_one_type_is_all_that_is_left(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = tuned_tools(rules, agent_random_die=1, agent_type_share_divisor=4)
    async with database.write() as session:
        peoples = [plain(await spawn(session, f"Folk {index}", EntityType.PEOPLE, world.core.world.id)) for index in range(3)]
        assert len(pick(tuned, peoples, 3, EPOCH, rng())) == 3


async def test_pick_always_keeps_forced_candidates_and_zero_count_returns_only_them(database: Database, world: AgentWorld, rules: Rules) -> None:
    tuned = die_one(rules)
    async with database.write() as session:
        forced = plain(await spawn(session, "Summoned", EntityType.SETTLEMENT, world.core.world.id, power=1), forced=True)
        others = [plain(await spawn(session, f"Folk {index}", EntityType.PEOPLE, world.core.world.id, power=9)) for index in range(3)]
        assert pick(tuned, [forced, *others], 0, EPOCH, rng()) == [forced]
        chosen = pick(tuned, [*others, forced], 2, EPOCH, rng())
        assert chosen[0] is forced and len(chosen) == 2


async def add_second_world(database: Database, names: tuple[str, ...]) -> tuple[int, list[int]]:
    async with database.write() as session:
        second, _ = await add_empty_world(session)
        ids = [(await spawn(session, name, EntityType.PEOPLE, second.id, power=5)).id for name in names]
        return second.id, ids


async def test_multi_world_selection_honours_a_manual_per_world_allowance(database: Database, world: AgentWorld, rules: Rules) -> None:
    second_id, second_ids = await add_second_world(database, ("Dune Kin", "Dune Herd", "Dune Clan"))
    async with database.write() as session:
        row = await session.get(WorldRow, second_id)
        assert row is not None
        row.mortal_agents = 1
    async with database.read() as session:
        picked = await choose_mortal_agents(await load_scope(session, rules), 6)
    from_second = [entity for entity in picked if entity.id in second_ids]
    assert len(from_second) == 1
    assert len(picked) > 1


async def test_multi_world_selection_gives_an_empty_allowance_no_picks_but_keeps_forced_ones(database: Database, world: AgentWorld, rules: Rules) -> None:
    second_id, second_ids = await add_second_world(database, ("Dune Kin", "Dune Herd"))
    async with database.write() as session:
        row = await session.get(WorldRow, second_id)
        assert row is not None
        row.mortal_agents = 0
    async with database.read() as session:
        picked = await choose_mortal_agents(await load_scope(session, rules), 6)
    assert not [entity for entity in picked if entity.id in second_ids]
    async with database.write() as session:
        await EntityRepository(session).add_flag(second_ids[0], EntityFlag.AGENT_SELECTED, 1)
    async with database.read() as session:
        picked = await choose_mortal_agents(await load_scope(session, rules), 6)
    assert second_ids[0] in [entity.id for entity in picked]


async def test_multi_world_automatic_shares_reach_every_world(database: Database, world: AgentWorld, rules: Rules) -> None:
    _, second_ids = await add_second_world(database, ("Dune Kin", "Dune Herd"))
    async with database.read() as session:
        picked = await choose_mortal_agents(await load_scope(session, rules), 3)
    assert any(entity.id in second_ids for entity in picked)
    assert any(entity.world_id == world.core.world.id for entity in picked)


async def test_candidates_mark_forced_and_exclude_those_who_already_acted(database: Database, world: AgentWorld, rules: Rules) -> None:
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.creation.id, EntityFlag.AGENT_SELECTED, 1)
        acted = await session.get(EntityRow, world.core.extra["town"].id)
        assert acted is not None
        acted.last_acted_epoch = 5
    async with database.read() as session:
        scope = await load_scope(session, rules)
        scope.cosmos.epoch = 5
        found = {candidate.entity.id: candidate for candidate in await candidates(scope)}
    assert found[world.creation.id].forced
    assert world.core.extra["town"].id not in found


async def test_begin_turn_resumes_with_the_saved_action_points(database: Database, world: AgentWorld) -> None:
    node = world.creation.id
    async with database.write() as session:
        fresh = await begin_turn(session, node, AgentKind.MORTAL, EPOCH, 5)
        assert not fresh.resumed and fresh.action_points == 5
        await save_turn(session, node, 2, fresh.context)
    async with database.write() as session:
        resumed = await begin_turn(session, node, AgentKind.MORTAL, EPOCH, 5)
        assert resumed.resumed and resumed.action_points == 2


async def test_begin_turn_starts_fresh_after_finish_or_in_a_later_epoch(database: Database, world: AgentWorld) -> None:
    node = world.creation.id
    async with database.write() as session:
        first = await begin_turn(session, node, AgentKind.MORTAL, EPOCH, 5)
        await save_turn(session, node, 2, first.context)
        later = await begin_turn(session, node, AgentKind.MORTAL, EPOCH + 1, 5)
        assert not later.resumed and later.action_points == 5
        await save_turn(session, node, 1, later.context)
        await finish_turn(session, node)
        again = await begin_turn(session, node, AgentKind.MORTAL, EPOCH + 1, 5)
        assert not again.resumed and again.action_points == 5
        row = await turn_row(session, node)
        assert row is not None and not row.finished


async def dream_for(database: Database, world: AgentWorld) -> int:
    async with database.write() as session:
        message = MessageRow(
            epoch=1,
            sender_node_id=world.core.son.id,
            recipient_node_id=world.creation.id,
            intent=MessageIntent.DREAM,
            text="The salt remembers you.",
        )
        session.add(message)
        await session.flush()
        return message.id


async def test_finishing_a_turn_marks_dreams_read_clears_the_selection_and_chronicles_the_word(
    runtime: AgentRuntime, database: Database, world: AgentWorld
) -> None:
    message_id = await dream_for(database, world)
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.creation.id, EntityFlag.AGENT_SELECTED, 1)
    started = StartedMortalTurn(world.creation.id, world.creation.name, EPOCH, False, 3, [message_id])
    result = await finish_mortal_turn(runtime, started, TurnOutcome("«We dig deep.»", SessionStatus.SUCCESS), [])
    assert isinstance(result, MortalTurnResult) and result.word == "We dig deep."
    async with database.read() as session:
        message = await session.get(MessageRow, message_id)
        entity = await session.get(EntityRow, world.creation.id)
        flagged = await EntityRepository(session).has_flag(world.creation.id, EntityFlag.AGENT_SELECTED)
        keys = list(await session.scalars(select(ChronicleRow.template_key)))
    assert message is not None and message.is_read
    assert entity is not None and entity.last_acted_epoch == EPOCH
    assert not flagged
    assert "mortal.word" in keys


async def test_a_full_mortal_turn_reads_the_pending_dream(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    message_id = await dream_for(database, world)
    model.runs.append(spoken("«We dig.»"))
    await run_mortal_turn(runtime, world.creation.id)
    async with database.read() as session:
        message = await session.get(MessageRow, message_id)
    assert message is not None and message.is_read


async def test_fate_reviews_mortal_creations_only_when_the_rule_is_on(database: Database, world: AgentWorld, rules: Rules) -> None:
    async with database.write() as session:
        creation = await EntityRepository(session).create(
            EntityDraft(
                name="Mortal Made",
                entity_type=EntityType.PEOPLE,
                description="A people shaped by a mortal hand.",
                stats=PeopleStats(population=500),
                power_level=2,
                origin=EntityOrigin.MORTAL,
                birth_epoch=1,
                world_id=world.core.world.id,
                maker_entity_id=world.core.extra["sage"].id,
                split_title=False,
            )
        )
        creation_id = creation.id
    async with database.read() as session:
        scope = await load_scope(session, rules)
        assert EntityOrigin.MORTAL in judge_origins(scope)
        reviewed = {entity.id for entity in await records_to_judge(scope, 1, scope.epoch)}
    assert creation_id in reviewed and world.creation.id in reviewed
    off = replace(rules, fate=replace(rules.fate, review_mortal_creations=0))
    async with database.read() as session:
        scope = await load_scope(session, off)
        assert EntityOrigin.MORTAL not in judge_origins(scope)
        reviewed = {entity.id for entity in await records_to_judge(scope, 1, scope.epoch)}
    assert creation_id not in reviewed and world.creation.id in reviewed
