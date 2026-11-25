import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from aerona.core.errors import BusyError, ConflictError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillArtifactRow, DivineWillPlanRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.divine_will import PlanStatus, StepImpact, StepStatus
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.services.container import Services
from aerona.services.discovery import DiscoveryService
from aerona.services.divine_will.library import PlanPlayer
from aerona.services.divine_will.plans import PlanDesk, plan_body
from aerona.services.ledger import Ledger
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.rules import RulesService
from aerona.settings import Settings
from aerona.tools.divine_will import plans as plan_tools
from aerona.tools.divine_will.framework import PlayerPort
from aerona.tools.divine_will.library_ports import PlanView, StepDraft
from tests.conftest import OpenDatabase
from tests.divine_will.library_fixtures import Heard, ScriptedPlayer, eventually, listening_bus, rule_steps
from tests.tools.every_divine_will_tool import HarnessApplication, HarnessServices
from tests.tools.factories import seed_realm

MOOD = "creator:mood"


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    found = open_database(tmp_path / "plans.db")
    await seed_realm(found)
    yield found
    await found.dispose()


def step(title: str, contentment: int, *, depends_on: tuple[int, ...] = (), impact: StepImpact = StepImpact.SAFE) -> StepDraft:
    return StepDraft(title=title, action_id=MOOD, input={"contentment": contentment}, depends_on=list(depends_on), declared_impact=impact)


def scripted_desk(database: Database, player: ScriptedPlayer) -> tuple[PlanDesk, JobManager, Heard]:
    bus, heard = listening_bus()
    jobs = JobManager(database, bus)
    return PlanDesk(database, bus, jobs, lambda _job: player, rule_steps(database, bus), poll_seconds=0.01), jobs, heard


def real_desk(database: Database, folder: Path) -> tuple[PlanDesk, JobManager]:
    bus = EventBus()
    jobs = JobManager(database, bus)
    settings = Settings(data_dir=folder, llm_enabled=False, image_worker_url="")
    host = cast(
        Services,
        HarnessServices(
            database, jobs, RulesService(database), HarnessApplication(Ledger(bus), DiscoveryService(settings)), PlayerRuntime(database, jobs, bus)
        ),
    )

    def player_for(job_id: str) -> PlayerPort:
        return PlanPlayer(host, job_id)

    return PlanDesk(database, bus, jobs, player_for, rule_steps(database, bus)), jobs


async def settled(desk: PlanDesk, jobs: JobManager, plan_id: int) -> PlanView:
    await eventually(lambda: asyncio.sleep(0, jobs.busy_group(WORLD_GROUP)), lambda holder: holder is None)
    return await desk.read(plan_id)


async def approved(desk: PlanDesk, steps: list[StepDraft]) -> PlanView:
    plan = await desk.create("Moods", steps, cycle_id=None)
    return await desk.approve(plan.id)


async def contentment(database: Database) -> int:
    async with database.read() as session:
        return int((await CosmosRepository(session).require_creator()).mood_contentment)


async def test_a_plan_checks_every_step_against_its_act(database: Database) -> None:
    desk, _, _ = scripted_desk(database, ScriptedPlayer())
    with pytest.raises(ValidationFailedError, match="no act called nowhere"):
        await desk.create("Bad", [StepDraft(title="x", action_id="nowhere")], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="did not fit"):
        await desk.create("Bad", [StepDraft(title="x", action_id=MOOD, input={"contentment": "lots"})], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="numbered 1 to 1"):
        await desk.create("Bad", [step("x", 50, depends_on=(3,))], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="in a circle"):
        await desk.create("Bad", [step("x", 50, depends_on=(2,)), step("y", 60, depends_on=(1,))], cycle_id=None)


async def test_an_approved_plan_runs_through_the_real_runner_and_each_step_undoes(database: Database, tmp_path: Path) -> None:
    desk, jobs = real_desk(database, tmp_path / "data")
    plan = await desk.create("Moods", [step("Lift", 61, depends_on=(2,)), step("Calm", 44)], cycle_id=None)
    with pytest.raises(ConflictError, match="not approved"):
        await desk.execute(plan.id)
    await desk.approve(plan.id)
    started = await desk.execute(plan.id)
    assert started.job_id
    done = await settled(desk, jobs, plan.id)
    assert done.status is PlanStatus.DONE
    assert [item.status for item in done.steps] == [StepStatus.DONE, StepStatus.DONE]
    assert all(item.ledger_entry_id is not None for item in done.steps)
    assert await contentment(database) == 61
    undone = await desk.undo(plan.id, 1)
    assert undone.steps[0].status is StepStatus.UNDONE
    assert await contentment(database) == 44
    async with database.read() as session:
        entry = await session.get(LedgerEntryRow, done.steps[0].ledger_entry_id)
        assert entry is not None and entry.undone
        assert done.artifact_id is not None
        mirror = await session.get(DivineWillArtifactRow, done.artifact_id)
        assert mirror is not None and mirror.current_version > 3
    with pytest.raises(ConflictError):
        await desk.undo(plan.id, 1)


async def test_a_paused_plan_finishes_its_step_and_resumes_where_it_stopped(database: Database) -> None:
    player = ScriptedPlayer(gate=asyncio.Event())
    desk, jobs, heard = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50), step("Two", 55)])
    await desk.execute(plan.id)
    await asyncio.wait_for(player.started.wait(), 30)
    paused = await desk.pause(plan.id)
    assert paused.status is PlanStatus.PAUSED
    assert player.gate is not None
    player.gate.set()
    stopped = await settled(desk, jobs, plan.id)
    assert stopped.status is PlanStatus.PAUSED
    assert [item.status for item in stopped.steps] == [StepStatus.DONE, StepStatus.PENDING]
    await desk.resume(plan.id)
    finished = await settled(desk, jobs, plan.id)
    assert finished.status is PlanStatus.DONE
    assert [name for name, _ in player.performed] == [MOOD, MOOD]
    assert {event.payload["status"] for event in heard.of(EventKind.DIVINE_WILL_PLAN_CHANGED)} >= {"draft", "approved", "running", "paused", "done"}


async def test_a_skipped_step_blocks_what_waits_for_it(database: Database) -> None:
    player = ScriptedPlayer()
    desk, jobs, _ = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50), step("Two", 55, depends_on=(1,))])
    await desk.skip(plan.id, 1)
    await desk.execute(plan.id)
    stopped = await settled(desk, jobs, plan.id)
    assert stopped.status is PlanStatus.PAUSED
    assert stopped.waiting_step == 2
    assert "waits for step 1" in stopped.steps[1].error
    assert player.performed == []
    await desk.skip(plan.id, 2)
    with pytest.raises(ConflictError, match="no step left"):
        await desk.execute(plan.id)


async def test_a_failed_step_stops_the_plan_until_it_is_skipped(database: Database) -> None:
    player = ScriptedPlayer(performs={MOOD: {"ok": False, "error": "The act was refused."}})
    desk, jobs, _ = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50), step("Two", 55)])
    await desk.execute(plan.id)
    failed = await settled(desk, jobs, plan.id)
    assert failed.status is PlanStatus.FAILED
    assert failed.steps[0].status is StepStatus.FAILED
    assert failed.steps[0].error == "The act was refused."
    assert failed.steps[1].status is StepStatus.PENDING
    await desk.skip(plan.id, 1)
    player.performs.clear()
    await desk.execute(plan.id)
    finished = await settled(desk, jobs, plan.id)
    assert finished.status is PlanStatus.DONE
    assert [item.status for item in finished.steps] == [StepStatus.SKIPPED, StepStatus.DONE]


async def test_a_step_whose_rehearsal_destroys_more_than_it_declared_stops_and_asks(database: Database) -> None:
    player = ScriptedPlayer(previews={MOOD: {"destructive": True, "deleted_nodes": [{"node_id": 9, "name": "Old Hall"}]}})
    desk, jobs, _ = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50)])
    await desk.execute(plan.id)
    asked = await settled(desk, jobs, plan.id)
    assert asked.status is PlanStatus.PAUSED
    assert asked.waiting_step == 1
    assert "did not declare" in asked.steps[0].error and "Old Hall" in asked.steps[0].error
    assert player.performed == []
    revised = await desk.revise(plan.id, [step("One", 50, impact=StepImpact.DESTRUCTIVE)])
    assert revised.status is PlanStatus.DRAFT
    assert revised.approved_at is None
    await desk.approve(plan.id)
    await desk.execute(plan.id)
    finished = await settled(desk, jobs, plan.id)
    assert finished.status is PlanStatus.DONE
    assert len(player.performed) == 1


async def test_a_costly_rehearsal_stops_a_step_declared_safe(database: Database) -> None:
    player = ScriptedPlayer(previews={MOOD: {"costly": True, "essence": 99}})
    desk, jobs, _ = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50), step("Two", 52, impact=StepImpact.COSTLY)])
    await desk.skip(plan.id, 1)
    await desk.execute(plan.id)
    assert (await settled(desk, jobs, plan.id)).status is PlanStatus.DONE
    again = await approved(desk, [step("Three", 53)])
    await desk.execute(again.id)
    asked = await settled(desk, jobs, again.id)
    assert asked.status is PlanStatus.PAUSED and "99 essence" in asked.steps[0].error


async def test_a_plan_refuses_to_run_while_the_world_is_busy(database: Database) -> None:
    desk, jobs, _ = scripted_desk(database, ScriptedPlayer())
    plan = await approved(desk, [step("One", 50)])
    release = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    await jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    with pytest.raises(BusyError, match="busy"):
        await desk.execute(plan.id)
    assert (await desk.read(plan.id)).status is PlanStatus.APPROVED
    release.set()
    await settled(desk, jobs, plan.id)
    await desk.execute(plan.id)
    assert (await settled(desk, jobs, plan.id)).status is PlanStatus.DONE


async def test_revising_keeps_finished_steps_in_place(database: Database) -> None:
    player = ScriptedPlayer()
    desk, jobs, _ = scripted_desk(database, player)
    plan = await approved(desk, [step("One", 50), step("Two", 55, depends_on=(3,)), step("Three", 60)])
    await desk.skip(plan.id, 3)
    await desk.execute(plan.id)
    stopped = await settled(desk, jobs, plan.id)
    assert [item.status for item in stopped.steps] == [StepStatus.DONE, StepStatus.PENDING, StepStatus.SKIPPED]
    with pytest.raises(ConflictError, match="keeps its place"):
        await desk.revise(plan.id, [step("One", 70), step("Two", 55), step("Three", 60)])
    with pytest.raises(ConflictError, match="keeps its place"):
        await desk.revise(plan.id, [step("One", 50)])
    revised = await desk.revise(plan.id, [step("Same", 50), step("Changed", 65), step("Three", 60), step("Added", 70, depends_on=(2,))], title="Moods again")
    assert revised.title == "Moods again"
    assert revised.status is PlanStatus.DRAFT
    assert [(item.title, item.status) for item in revised.steps] == [
        ("Same", StepStatus.DONE),
        ("Changed", StepStatus.PENDING),
        ("Three", StepStatus.SKIPPED),
        ("Added", StepStatus.PENDING),
    ]
    await desk.approve(plan.id)
    await desk.execute(plan.id)
    finished = await settled(desk, jobs, plan.id)
    assert finished.status is PlanStatus.DONE
    assert [payload["contentment"] for _, payload in player.performed] == [50, 65, 70]
    abandoned = await desk.abandon((await approved(desk, [step("Later", 40)])).id)
    assert abandoned.status is PlanStatus.ABANDONED
    with pytest.raises(ConflictError):
        await desk.approve(abandoned.id)


async def test_a_rule_step_is_checked_run_and_undone_like_an_act(database: Database) -> None:
    player = ScriptedPlayer()
    desk, jobs, _ = scripted_desk(database, player)
    with pytest.raises(ValidationFailedError, match=r"no rule divine_will\.nothing"):
        await desk.create(
            "Rules", [StepDraft(title="x", action_id="rule:set", input={"namespace": "divine_will", "name": "nothing", "value": 1})], cycle_id=None
        )
    with pytest.raises(ValidationFailedError, match="give value"):
        await desk.create("Rules", [StepDraft(title="x", action_id="rule:set", input={"namespace": "divine_will", "name": "page_tokens"})], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="takes no value"):
        await desk.create(
            "Rules", [StepDraft(title="x", action_id="rule:reset", input={"namespace": "divine_will", "name": "page_tokens", "value": 1})], cycle_id=None
        )
    widen = StepDraft(title="Wider pages", action_id="rule:set", input={"namespace": "divine_will", "name": "page_tokens", "value": 7000})
    plan = await approved(desk, [widen, step("Then the mood", 52, depends_on=(1,))])
    assert plan.steps[0].action_title == "Set a rule of the world"
    await desk.execute(plan.id)
    done = await settled(desk, jobs, plan.id)
    assert [item.status for item in done.steps] == [StepStatus.DONE, StepStatus.DONE]
    assert "6000 to 7000" in done.steps[0].result_text
    assert desk.rules.desk.rules.current.divine_will.page_tokens == 7000
    assert done.steps[0].input["was_default"] is True
    undone = await desk.undo(plan.id, 1)
    assert undone.steps[0].status is StepStatus.UNDONE
    assert desk.rules.desk.rules.current.divine_will.page_tokens == 6000
    assert [name for name, _ in player.performed] == [MOOD]
    narrow = StepDraft(title="Too narrow", action_id="rule:set", input={"namespace": "divine_will", "name": "page_tokens", "value": 10})
    with pytest.raises(ValidationFailedError, match=r"at least 500\.$"):
        await approved(desk, [narrow])


def test_an_abandoned_plan_tells_the_model_not_to_write_it_again() -> None:
    view = PlanView(4, "A plan", PlanStatus.ABANDONED, None, None, None, None, datetime.now(UTC), [])
    assert "Do not write it again unless the player asks" in plan_tools.plan_head(view)
    paused = PlanView(5, "A plan", PlanStatus.PAUSED, None, None, None, None, datetime.now(UTC), [])
    assert "only when the player resumes it" in plan_tools.plan_head(paused)


def test_the_plan_text_names_its_own_status_and_writes_times_like_the_book() -> None:
    moment = datetime(2026, 11, 25, 4, 10, tzinfo=UTC)
    plan = DivineWillPlanRow(id=1, title="A plan", status=PlanStatus.DONE, approved_at=moment, finished_at=moment)
    body = plan_body(plan, [])
    assert "**Plan status:** Done" in body
    assert "**Status:**" not in body
    assert "2026-11-25 04:10" in body
    assert "T04:10" not in body
