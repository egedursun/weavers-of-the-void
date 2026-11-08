import asyncio
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from aerona.db.session import Database
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.job import JobStatus
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.player.catalog import ACTIONS, action, run_job
from aerona.services.player.ports import ContentJob, CreativePorts, RevelationRequest, WorldCreationRequest
from aerona.services.player.runtime import PlayerRuntime
from tests.services.player.every_lever import Lever, Pick, foreign_god, payload_for

JOB_ACTIONS = sorted(spec.id for spec in ACTIONS if spec.job is not None)
JOBS: Mapping[str, Lever] = {
    "son:epic": Lever(values={"son_id": Pick("son")}),
    "son:birth_child": Lever(values={"son_id": Pick("son"), "inspiration": "a child of the tides"}),
    "revelation": Lever(values={"content": "The rivers remember their first course."}),
    "create_world": Lever(values={"inspiration": "a world of slow tides"}),
    "awaken_peoples": Lever(values={"count": 1}),
    "foreign_god:place": Lever(values={"world_id": Pick("world"), "name": "Old Moru"}),
    "foreign_god:deepen": Lever(values={"god_id": Pick("foreign_god")}, setup=foreign_god),
    "foreign_god:wake": Lever(values={"god_id": Pick("foreign_god")}, setup=foreign_god),
    "mortal:act": Lever(values={"entity_id": Pick(EntityType.MORTAL)}),
    "chronicle:audit": Lever(values={"epoch": 1}),
}


class Ports:
    async def summon(self, world_id: int | None) -> int:
        return 1

    async def birth(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> int:
        return parent_son_id

    async def act(self, entity_id: int) -> str:
        return "acted"

    async def reveal(self, request: RevelationRequest) -> int:
        return len(request.content)

    async def create(self, request: WorldCreationRequest) -> int:
        return len(request.inspiration)

    async def awaken(self, count: int, world_id: int | None) -> list[int]:
        return list(range(count))

    async def write(self, job: ContentJob) -> str:
        return "written"

    async def tally(self) -> dict[str, int]:
        return {"done": 1}

    async def retry_fate(self) -> dict[str, int]:
        return await self.tally()

    async def rejudge_debt(self) -> dict[str, int]:
        return await self.tally()

    async def rejudge_limbo(self) -> dict[str, int]:
        return await self.tally()

    async def retry_voices(self) -> dict[str, int]:
        return await self.tally()

    async def retry_births(self) -> dict[str, int]:
        return await self.tally()

    async def audit_chronicle(self, epoch: int) -> dict[str, int]:
        return await self.tally()


async def finished(runtime: PlayerRuntime, job_id: Any) -> tuple[JobStatus, str | None]:
    assert isinstance(job_id, str)
    for _ in range(500):
        row = await runtime.jobs.get(job_id)
        if row.status in (JobStatus.SUCCEEDED.value, JobStatus.FAILED.value):
            return JobStatus(row.status), row.error
        await asyncio.sleep(0.01)
    raise AssertionError("the job did not finish")


def test_every_job_case_names_a_real_job() -> None:
    assert set(JOBS) <= set(JOB_ACTIONS)


@pytest.mark.parametrize("action_id", JOB_ACTIONS)
async def test_every_god_job_runs_to_success(lever_template: Path, tmp_path: Path, action_id: str) -> None:
    path = tmp_path / "job.db"
    shutil.copyfile(lever_template, path)
    database = Database(f"sqlite+aiosqlite:///{path}")
    bus = EventBus()
    jobs = JobManager(database, bus)
    ports = Ports()
    runtime = PlayerRuntime(
        database, jobs, bus, CreativePorts(summoner=ports, revelations=ports, worlds=ports, awakener=ports, writer=ports, fate=ports, mortals=ports)
    )
    lever = JOBS.get(action_id, Lever())
    try:
        if lever.setup is not None:
            async with database.write() as session:
                await lever.setup(session)
        async with database.read() as session:
            payload = await payload_for(session, action(action_id).input_model, lever.values, 1)
        outcome = await run_job(runtime, Rules(), action_id, payload)
        status, error = await finished(runtime, outcome.values["job_id"])
        assert status is JobStatus.SUCCEEDED, error
    finally:
        await jobs.shutdown()
        await database.dispose()
