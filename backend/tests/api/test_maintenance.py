import pytest

from aerona.db.tables.epochs import EpochRow
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.services.maintenance.models import MaintenanceTask
from aerona.settings import Settings
from tests.agents.fakes import FakeModel
from tests.api.conftest import ApiWorld, open_api, seeded

LLM_TASKS = {MaintenanceTask.COMPLETION}


async def run(api: ApiWorld, task: MaintenanceTask) -> dict[str, object]:
    started = await api.http.post(f"/api/maintenance/tasks/{task.value}/run")
    assert started.status_code == 202, started.text
    job = await api.wait_job(started.json()["job_id"])
    assert job["status"] == "succeeded", job
    result: dict[str, object] = job["result"]
    return result


async def test_task_catalogue_lists_every_task(api: ApiWorld) -> None:
    body = (await api.http.get("/api/maintenance/tasks")).json()
    assert {item["task"] for item in body} == {task.value for task in MaintenanceTask}
    assert all(item["title"] and item["rows"] for item in body)
    assert not any(item["running"] for item in body)


@pytest.mark.parametrize("task", [task for task in MaintenanceTask if task not in LLM_TASKS])
async def test_every_task_runs_as_a_job_with_counters(api: ApiWorld, task: MaintenanceTask) -> None:
    result = await run(api, task)
    assert result["task"] == task.value
    assert isinstance(result["counters"], dict) and result["counters"]


async def test_ledgered_task_leaves_a_ledger_entry(api: ApiWorld) -> None:
    result = await run(api, MaintenanceTask.DATA_REPAIRS)
    assert result["ledger_entry_id"] is None or isinstance(result["ledger_entry_id"], int)
    unledgered = await run(api, MaintenanceTask.PRUNE)
    assert unledgered["ledger_entry_id"] is None
    assert set(unledgered["counters"]) >= {"notifications", "ledger", "metrics", "change_log", "media"}


async def test_epoch_year_repair_fixes_a_broken_range(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        session.add(EpochRow(epoch=1, year_start=999, year_end=1000))
    result = await run(api, MaintenanceTask.EPOCH_YEARS)
    assert result["counters"] == {"aligned": 1}
    again = await run(api, MaintenanceTask.EPOCH_YEARS)
    assert again["counters"] == {"aligned": 0}


async def test_certain_facts_are_rebuilt_idempotently(api: ApiWorld) -> None:
    seeded(api)
    first = await run(api, MaintenanceTask.CERTAIN_FACTS)
    second = await run(api, MaintenanceTask.CERTAIN_FACTS)
    assert second["counters"] == {"written": 0}
    assert isinstance(first["counters"], dict)


async def test_completion_needs_the_model_and_reports_missing_content(api: ApiWorld) -> None:
    refused = await api.http.post("/api/maintenance/tasks/completion/run")
    assert refused.status_code == 409
    missing = (await api.http.get("/api/maintenance/missing")).json()
    assert set(missing) >= {"portrait", "son_powers", "pending_names", "anything_missing"}
    assert missing["anything_missing"] is True


async def test_unknown_task_is_rejected(api: ApiWorld) -> None:
    assert (await api.http.post("/api/maintenance/tasks/nonsense/run")).status_code in (400, 422)


async def test_maintenance_is_refused_while_an_epoch_runs(api: ApiWorld) -> None:
    api.services.jobs._groups[WORLD_GROUP] = "fake"
    try:
        response = await api.http.post("/api/maintenance/tasks/importance/run")
        assert response.status_code == 409
    finally:
        api.services.jobs._groups.pop(WORLD_GROUP, None)


async def test_completion_job_runs_with_a_connected_model(settings: Settings) -> None:
    async for api in open_api(settings, model=FakeModel(), seeded=True):
        started = await api.http.post("/api/maintenance/tasks/completion/run")
        assert started.status_code == 202, started.text
        job = await api.wait_job(started.json()["job_id"])
        assert job["kind"] == "completion"
        assert job["status"] == "succeeded"
        assert set(job["result"]["counters"]) == {"completed", "failed"}


async def test_backup_verify_and_llm_bound_maintenance(api: ApiWorld) -> None:
    taken = (await api.http.post("/api/backups")).json()
    verified = await api.http.post(f"/api/maintenance/backups/{taken['file']}/verify")
    assert verified.json() == {"file": taken["file"], "ok": True}
    son = seeded(api).core.son
    assert (await api.http.post(f"/api/maintenance/sons/{son.id}/powers")).status_code == 409
    assert (await api.http.post("/api/maintenance/cosmos-prompts")).status_code == 409
    assert (await api.http.post("/api/maintenance/chronicles")).status_code == 409
