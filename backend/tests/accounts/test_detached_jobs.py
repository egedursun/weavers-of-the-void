from pathlib import Path
from typing import Any

from aerona.core.account_scope import CURRENT_ACCOUNT, AccountRef, current_account
from aerona.domain.enums.accounts import Permission, UniverseRole
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.events.bus import EventBus
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.services.accounts.access import UniverseAccess
from aerona.services.accounts.guard import GrantedAccess, current_grant, ensure_lever_allowed, enter_grant
from tests.conftest import OpenDatabase
from tests.polling import until

EDITOR_WITHOUT_CANON = UniverseAccess(
    universe_id="aaaaaaaaaaaa",
    workspace_id=1,
    workspace_role=None,
    role=UniverseRole.EDITOR,
    overridden=False,
    permissions=frozenset(Permission) - {Permission.LOCK_CANON},
)


async def finished(manager: JobManager, job_id: str) -> str:
    async def done() -> bool:
        return (await manager.get(job_id)).status in {JobStatus.SUCCEEDED.value, JobStatus.FAILED.value}

    assert await until(done)
    return str((await manager.get(job_id)).status)


async def test_an_engine_job_started_by_a_person_runs_as_nobody_while_a_person_job_keeps_them(tmp_path: Path, open_database: OpenDatabase) -> None:
    manager = JobManager(open_database(tmp_path / "jobs.db"), EventBus())
    seen: dict[str, Any] = {}

    def watcher(key: str) -> Any:
        async def work(context: JobContext) -> dict[str, Any]:
            seen[key] = (current_account(), current_grant())
            ensure_lever_allowed("lever:suppress")
            return {}

        return work

    CURRENT_ACCOUNT.set(AccountRef(7, "Editor"))
    enter_grant(GrantedAccess(EDITOR_WITHOUT_CANON, "Haluvra", canon_approval=False))
    try:
        engine = await manager.submit(JobKind.EPOCH, watcher("engine"))
        person = await manager.submit(JobKind.DIVINE_WILL, watcher("person"), as_person=True)
        assert await finished(manager, engine) == JobStatus.SUCCEEDED.value
        assert await finished(manager, person) == JobStatus.FAILED.value
    finally:
        enter_grant(None)
        CURRENT_ACCOUNT.set(None)
    assert seen["engine"] == (None, None)
    assert seen["person"][0] == AccountRef(7, "Editor")
    await manager.shutdown()
