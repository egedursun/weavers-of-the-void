import asyncio
from collections.abc import AsyncIterator

import pytest

from aerona.core.errors import BusyError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.job import JobStatus
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.player import catalog, creation, creator, interventions
from aerona.services.player.ports import ContentJob, CreativePorts, RevelationRequest, WorldCreationRequest
from aerona.services.player.runtime import PlayerRuntime
from tests.services.player.factories import make_entity, make_son, seed_player_world


class FakeSummoner:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[int | None] = []

    async def summon(self, world_id: int | None) -> int:
        self.calls.append(world_id)
        if self.fail:
            raise RuntimeError("the summoning failed")
        return 77


class FakeRevelations:
    async def reveal(self, request: RevelationRequest) -> int:
        return len(request.content)


class FakeWorlds:
    async def create(self, request: WorldCreationRequest) -> int:
        return len(request.inspiration)


class FakeAwakener:
    def __init__(self) -> None:
        self.batches: list[int] = []

    async def awaken(self, count: int, world_id: int | None) -> list[int]:
        self.batches.append(count)
        return list(range(count))


class FakeWriter:
    def __init__(self) -> None:
        self.jobs: list[ContentJob] = []

    async def write(self, job: ContentJob) -> str:
        self.jobs.append(job)
        return "written"


@pytest.fixture
async def seeded(database: Database) -> int:
    async with database.write() as session:
        world = await seed_player_world(session)
        return world.world.id


@pytest.fixture
async def runtime(database: Database, seeded: int) -> AsyncIterator[PlayerRuntime]:
    bus = EventBus()
    jobs = JobManager(database, bus)
    ports = CreativePorts(summoner=FakeSummoner(), revelations=FakeRevelations(), worlds=FakeWorlds(), awakener=FakeAwakener(), writer=FakeWriter())
    yield PlayerRuntime(database, jobs, bus, ports)
    await jobs.shutdown()


async def _finish(runtime: PlayerRuntime, job_id: object) -> JobStatus:
    assert isinstance(job_id, str)
    for _ in range(200):
        row = await runtime.jobs.get(job_id)
        if row.status in (JobStatus.SUCCEEDED.value, JobStatus.FAILED.value):
            return JobStatus(row.status)
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


async def _essence(database: Database) -> int:
    async with database.read() as session:
        return (await CosmosRepository(session).require_creator()).essence


async def test_summon_charges_and_publishes(runtime: PlayerRuntime, database: Database, rules: Rules, seeded: int) -> None:
    before = await _essence(database)
    outcome = await creation.summon_son(runtime, rules, creation.SummonSon(world_id=seeded))
    assert outcome.essence_spent == rules.costs.summon_son
    assert await _finish(runtime, outcome.values["job_id"]) is JobStatus.SUCCEEDED
    assert await _essence(database) == before - rules.costs.summon_son
    assert any(event.kind is EventKind.NEW_SON for event in runtime.bus.replay_after(0))


async def test_failed_summon_refunds(runtime: PlayerRuntime, database: Database, rules: Rules) -> None:
    failing = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus, CreativePorts(summoner=FakeSummoner(fail=True)))
    before = await _essence(database)
    outcome = await creation.summon_son(failing, rules, creation.SummonSon())
    assert await _finish(failing, outcome.values["job_id"]) is JobStatus.FAILED
    assert await _essence(database) == before


async def test_busy_lock_and_missing_port(runtime: PlayerRuntime, database: Database, rules: Rules) -> None:
    gate = asyncio.Event()

    class SlowSummoner:
        async def summon(self, world_id: int | None) -> int:
            await gate.wait()
            return 1

    slow = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus, CreativePorts(summoner=SlowSummoner()))
    first = await creation.summon_son(slow, rules, creation.SummonSon())
    with pytest.raises(BusyError):
        await creation.summon_son(slow, rules, creation.SummonSon())
    gate.set()
    assert await _finish(slow, first.values["job_id"]) is JobStatus.SUCCEEDED
    empty = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus)
    with pytest.raises(ValidationFailedError):
        await creation.summon_son(empty, rules, creation.SummonSon())


async def test_revelation_world_and_awakening(runtime: PlayerRuntime, database: Database, rules: Rules) -> None:
    with pytest.raises(ValidationFailedError):
        await interventions.revelation(runtime, rules, interventions.Revelation(content="  "))
    revealed = await interventions.revelation(runtime, rules, interventions.Revelation(content="Let there be salt."))
    assert await _finish(runtime, revealed.values["job_id"]) is JobStatus.SUCCEEDED
    world = await creation.create_world(runtime, rules, creation.CreateWorld(inspiration="x" * 5000))
    assert await _finish(runtime, world.values["job_id"]) is JobStatus.SUCCEEDED
    count = rules.awakening.batch_cap + 1
    awakened = await creation.awaken_peoples(runtime, rules, creation.AwakenPeoples(count=count))
    assert awakened.essence_spent == creation.awakening_cost(rules, count)
    assert await _finish(runtime, awakened.values["job_id"]) is JobStatus.SUCCEEDED
    awakener = runtime.ports.awakener
    assert isinstance(awakener, FakeAwakener)
    assert awakener.batches == [rules.awakening.batch_cap, 1]


async def test_content_jobs_and_foreign_god_place(runtime: PlayerRuntime, database: Database, rules: Rules, seeded: int) -> None:
    portrait = await creator.write_creator_content(runtime, rules, creator.CreatorContent())
    assert await _finish(runtime, portrait.values["job_id"]) is JobStatus.SUCCEEDED
    placed = await catalog.run_job(runtime, rules, "foreign_god:place", {"world_id": seeded, "name": "Old Moru"})
    assert placed.ledger_entry_id is not None
    assert await _finish(runtime, placed.values["job_id"]) is JobStatus.SUCCEEDED
    writer = runtime.ports.writer
    assert isinstance(writer, FakeWriter)
    assert [job.kind.value for job in writer.jobs] == ["creator_portrait", "foreign_god_deepen"]


async def test_placing_a_foreign_god_keeps_its_image_prompt(runtime: PlayerRuntime, database: Database, rules: Rules, seeded: int) -> None:
    command = {"world_id": seeded, "name": "Veiled Asha", "image_prompt": "  a veiled goddess of ash, gold leaf  "}
    placed = await catalog.run_job(runtime, rules, "foreign_god:place", command)
    assert placed.target_node_id is not None
    async with database.read() as session:
        god = await session.get(ForeignGodRow, placed.target_node_id)
    assert god is not None
    assert god.image_prompt == "a veiled goddess of ash, gold leaf"
    blank = await catalog.run_job(runtime, rules, "foreign_god:place", {"world_id": seeded, "name": "Bare Oru", "image_prompt": "   "})
    async with database.read() as session:
        bare = await session.get(ForeignGodRow, blank.target_node_id)
    assert bare is not None
    assert bare.image_prompt is None


async def test_waking_a_foreign_god_queues_a_rewrite(runtime: PlayerRuntime, database: Database, rules: Rules, seeded: int) -> None:
    placed = await catalog.run_job(runtime, rules, "foreign_god:place", {"world_id": seeded, "name": "Sleeping Varr"})
    assert await _finish(runtime, placed.values["job_id"]) is JobStatus.SUCCEEDED
    assert placed.target_node_id is not None
    woke = await catalog.run_job(runtime, rules, "foreign_god:wake", {"god_id": placed.target_node_id})
    assert woke.ledger_entry_id is not None
    assert await _finish(runtime, woke.values["job_id"]) is JobStatus.SUCCEEDED
    writer = runtime.ports.writer
    assert isinstance(writer, FakeWriter)
    assert writer.jobs[-1].kind.value == "foreign_god_awakened"
    assert writer.jobs[-1].target_id == placed.target_node_id


class FakeBirths:
    def __init__(self) -> None:
        self.births: list[tuple[int, str, int | None]] = []

    async def summon(self, world_id: int | None) -> int:
        return 0

    async def birth(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> int:
        self.births.append((parent_son_id, inspiration, co_parent_son_id))
        return 99


class FakeMortals:
    def __init__(self) -> None:
        self.turns: list[int] = []

    async def act(self, entity_id: int) -> str:
        self.turns.append(entity_id)
        return "ash"


async def test_creator_orders_a_child_and_a_mortal_turn(runtime: PlayerRuntime, database: Database, rules: Rules, seeded: int) -> None:
    async with database.write() as session:
        parent = await make_son(session, "Velkar", seeded)
        partner = await make_son(session, "Morvain", seeded)
        mortal = await make_entity(session, "Orrin", EntityType.MORTAL, world_id=seeded)
        parent_id, partner_id, mortal_id = parent.id, partner.id, mortal.id
    births, mortals = FakeBirths(), FakeMortals()
    ordered = PlayerRuntime(runtime.database, runtime.jobs, runtime.bus, CreativePorts(summoner=births, mortals=mortals))
    before = await _essence(database)
    child = await creation.birth_child(ordered, rules, creation.BirthChild(son_id=parent_id, inspiration="  a child of tides ", co_parent_id=partner_id))
    assert await _finish(ordered, child.values["job_id"]) is JobStatus.SUCCEEDED
    assert births.births == [(parent_id, "a child of tides", partner_id)]
    assert await _essence(database) == before
    assert any(event.kind is EventKind.NEW_SON and event.payload["son_id"] == 99 for event in runtime.bus.replay_after(0))
    with pytest.raises(ValidationFailedError):
        await creation.birth_child(ordered, rules, creation.BirthChild(son_id=parent_id, co_parent_id=parent_id))
    turn = await creation.mortal_act(ordered, rules, creation.MortalTarget(entity_id=mortal_id))
    assert await _finish(ordered, turn.values["job_id"]) is JobStatus.SUCCEEDED
    assert mortals.turns == [mortal_id]
    with pytest.raises(ValidationFailedError):
        await creation.mortal_act(runtime, rules, creation.MortalTarget(entity_id=mortal_id))
    assert {"son:birth_child", "mortal:act"} <= set(catalog.ACTIONS_BY_ID)
