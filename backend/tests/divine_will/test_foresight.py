import asyncio
import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import select

from aerona.core.errors import BusyError, ConflictError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochEnginePhaseRow, EpochRunRow
from aerona.domain.enums.divine_will import ForecastStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.epoch import EngineStage
from aerona.domain.enums.job import JobKind
from aerona.engine.primitives.stats import base_stat
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.divine_will.foresight import FALLBACK_EPOCH_SECONDS, FORECAST_WORKER, Foresight, rule_on_copy
from aerona.tools.divine_will import foresight as foresight_tools
from aerona.tools.divine_will.framework import WillCall
from aerona.tools.divine_will.library_ports import ForecastView, Intervention
from tests.conftest import OpenDatabase
from tests.divine_will.library_fixtures import Heard, eventually, listening_bus

RULES = Rules()


@pytest.fixture
async def fresh(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    found = open_database(tmp_path / "fresh.db")
    yield found
    await found.dispose()


@pytest.fixture
async def lived(tmp_path: Path, lever_template: Path) -> AsyncIterator[Database]:
    path = tmp_path / "lived.db"
    shutil.copyfile(lever_template, path)
    found = Database(f"sqlite+aiosqlite:///{path}")
    yield found
    await found.dispose()


def foresight_on(database: Database, root: Path) -> tuple[Foresight, JobManager, Heard]:
    bus, heard = listening_bus()
    jobs = JobManager(database, bus)
    return Foresight(database, bus, jobs, root), jobs, heard


async def finished(foresight: Foresight, forecast_id: int) -> ForecastView:
    return await eventually(lambda: foresight.read(forecast_id), lambda view: view.status not in (ForecastStatus.QUEUED, ForecastStatus.RUNNING), 600)


def my_workers() -> list[str]:
    listing = subprocess.run(["ps", "-ax", "-o", "ppid=,command="], capture_output=True, text=True, check=True).stdout
    rows = [line.strip().split(maxsplit=1) for line in listing.splitlines() if line.strip()]
    return [row[1] for row in rows if len(row) == 2 and row[0] == str(os.getpid()) and FORECAST_WORKER in row[1]]


async def test_the_estimate_reads_the_last_epochs_engine_seconds(fresh: Database, tmp_path: Path) -> None:
    foresight, _, _ = foresight_on(fresh, tmp_path / "forecasts")
    guessed = await foresight.estimate(2, RULES)
    assert (guessed.seconds_per_epoch, guessed.measured_epoch, guessed.from_forecast_id) == (FALLBACK_EPOCH_SECONDS, None, None)
    assert guessed.eta_seconds == 77
    async with fresh.write() as session:
        session.add_all([EpochRunRow(epoch=3), EpochRunRow(epoch=4)])
        await session.flush()
        session.add_all(
            [
                EpochEnginePhaseRow(epoch=3, stage=EngineStage.TICK, phase="a", seconds=99.0),
                EpochEnginePhaseRow(epoch=4, stage=EngineStage.TICK, phase="a", seconds=20.0),
                EpochEnginePhaseRow(epoch=4, stage=EngineStage.TRANSITION, phase="b", seconds=8.0),
            ]
        )
    measured = await foresight.estimate(3, RULES)
    assert (measured.seconds_per_epoch, measured.measured_epoch, measured.eta_seconds) == (28.0, 4, 105)
    with pytest.raises(ValidationFailedError, match="up to 3 epochs"):
        await foresight.estimate(4, RULES)
    wider = replace(RULES, divine_will=replace(RULES.divine_will, forecast_max_epochs=5))
    assert (await foresight.estimate(5, wider)).eta_seconds == 169


async def test_a_forecast_refuses_job_acts_unknown_acts_and_a_busy_world(fresh: Database, tmp_path: Path) -> None:
    foresight, jobs, _ = foresight_on(fresh, tmp_path / "forecasts")
    with pytest.raises(ValidationFailedError, match="needs the language model"):
        await foresight.run([Intervention(action_id="summon_son", input={})], 1, cycle_id=None, rules=RULES)
    with pytest.raises(ValidationFailedError, match="no act called"):
        await foresight.run([Intervention(action_id="nowhere")], 1, cycle_id=None, rules=RULES)
    with pytest.raises(ValidationFailedError, match="did not fit"):
        await foresight.run([Intervention(action_id="creator:mood", input={"contentment": "high"})], 1, cycle_id=None, rules=RULES)
    release = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, int]:
        await release.wait()
        return {}

    await jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    with pytest.raises(BusyError, match="busy"):
        await foresight.run([], 1, cycle_id=None, rules=RULES)
    release.set()


async def test_a_one_epoch_forecast_differs_where_the_intervention_acts(lived: Database, tmp_path: Path) -> None:
    async with lived.read() as session:
        people = await session.scalar(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id).limit(1)
        )
        assert people is not None
        population = base_stat(people, "population")
        assert population is not None
        target, before = people.id, population
    raised = before * 20 + 5000
    root = tmp_path / "forecasts"
    foresight, _, heard = foresight_on(lived, root)
    intervention = Intervention(action_id="entity:stat", input={"entity_id": target, "stat": "population", "value": raised})
    started = await foresight.run([intervention], 1, cycle_id=None, rules=RULES)
    assert started.status is ForecastStatus.QUEUED
    assert started.eta_seconds > 0
    done = await finished(foresight, started.id)
    assert done.status is ForecastStatus.DONE, done.error
    report = done.report
    assert report is not None
    assert report.end_epoch == report.start_epoch + 1
    assert [item.action_id for item in report.interventions] == ["entity:stat"]
    baseline = {node.node_id: node for node in report.baseline.nodes}
    intervened = {node.node_id: node for node in report.intervened.nodes}
    assert target in baseline and target in intervened
    assert intervened[target].stats["population"] > baseline[target].stats["population"]
    assert report.intervened.population > report.baseline.population
    assert report.baseline.chronicle and report.intervened.chronicle
    assert done.epochs_done == 1
    progress = heard.of(EventKind.DIVINE_WILL_FORECAST_PROGRESS)
    assert {event.payload["status"] for event in progress} >= {"queued", "running", "done"}
    assert any(event.payload["done_epochs"] == 1 for event in progress)
    assert not any(root.iterdir())
    async with lived.read() as session:
        world_people = await session.get(EntityRow, target)
        assert world_people is not None and base_stat(world_people, "population") == before
    again = await foresight.estimate(1, RULES)
    assert again.from_forecast_id == done.id or again.measured_epoch is not None


async def test_cancelling_a_forecast_stops_its_workers_and_removes_its_copies(lived: Database, tmp_path: Path) -> None:
    root = tmp_path / "forecasts"
    foresight, _, _ = foresight_on(lived, root)
    started = await foresight.run([], 1, cycle_id=None, rules=RULES)
    folder = root / f"forecast-{started.id}"
    await eventually(lambda: asyncio.sleep(0, my_workers()), lambda found: len(found) == 2, 120)
    await eventually(lambda: asyncio.sleep(0, folder.exists()), bool, 120)
    cancelled = await foresight.cancel(started.id)
    assert cancelled.status is ForecastStatus.CANCELLED
    assert cancelled.report is None
    assert not folder.exists()
    assert my_workers() == []
    with pytest.raises(ConflictError, match="already ended"):
        await foresight.cancel(started.id)


async def test_a_rule_intervention_is_checked_and_changes_only_the_copys_rules(lived: Database, tmp_path: Path) -> None:
    foresight, _jobs, _ = foresight_on(lived, tmp_path / "forecasts")
    with pytest.raises(ValidationFailedError, match="no rule"):
        await foresight.run([Intervention(action_id="rule:set", input={"namespace": "nowhere", "name": "nothing", "value": 1})], 1, cycle_id=None, rules=RULES)
    with pytest.raises(ValidationFailedError, match="takes no value"):
        await foresight.run(
            [Intervention(action_id="rule:reset", input={"namespace": "events", "name": "plague_peak_death_pct", "value": 1})], 1, cycle_id=None, rules=RULES
        )
    applied = await rule_on_copy(lived, 1, Intervention(action_id="rule:set", input={"namespace": "events", "name": "plague_peak_death_pct", "value": 40}))
    assert applied.action_id == "rule:set" and "40" in applied.message
    async with lived.read() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        assert rules_from_snapshot(cosmos.rules_snapshot).events.plague_peak_death_pct == 40


class Unfolding:
    def __init__(self, reads_before_done: int) -> None:
        self.left = reads_before_done

    async def read(self, forecast_id: int) -> ForecastView:
        self.left -= 1
        status = ForecastStatus.RUNNING if self.left > 0 else ForecastStatus.DONE
        return ForecastView(forecast_id, None, 1, status, 30, [], None, "", "", 0, None, None, datetime.now(UTC))


def test_a_cancelled_forecast_tells_the_model_not_to_run_it_again() -> None:
    view = ForecastView(3, None, 2, ForecastStatus.CANCELLED, 60, [], None, "", "", 0, None, None, datetime.now(UTC))
    assert "Do not run it again unless the player asks" in foresight_tools.forecast_head(view)


async def test_reading_a_running_forecast_waits_for_its_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foresight_tools, "POLL_SECONDS", 0.0)
    unfolding = Unfolding(reads_before_done=4)
    call = cast(WillCall, SimpleNamespace(services=SimpleNamespace(library=SimpleNamespace(foresight=unfolding))))
    view = await foresight_tools.finished_forecast(call, 1)
    assert view.status is ForecastStatus.DONE
    assert unfolding.left == 0
