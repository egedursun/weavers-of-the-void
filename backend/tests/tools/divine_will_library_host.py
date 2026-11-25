from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from aerona.db.session import Database
from aerona.domain.enums.job import JobKind
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobHandler, JobManager
from aerona.services.container import Services
from aerona.services.discovery import DiscoveryService
from aerona.services.divine_will.artifacts import ArtifactLibrary
from aerona.services.divine_will.foresight import Foresight
from aerona.services.divine_will.library import DivineWillLibrary, PlanPlayer, artifact_ranker
from aerona.services.divine_will.plans import PlanDesk
from aerona.services.divine_will.rule_steps import RuleSteps
from aerona.services.ledger import Ledger
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.rule_changes import RuleDesk
from aerona.services.rules import RulesService
from aerona.settings import Settings
from aerona.tools.divine_will.framework import PlayerPort
from tests.tools.divine_will_media import harness_index

DATA_FOLDER = "will-data"
FORECAST_FOLDER = "will-forecasts"


@dataclass
class LibraryApplication:
    ledger: Ledger
    discovery: DiscoveryService


@dataclass
class LibraryServices:
    database: Database
    jobs: JobManager
    rules: RulesService
    application: LibraryApplication
    player: PlayerRuntime


@dataclass(frozen=True)
class QueuedJob:
    kind: JobKind
    handler: JobHandler
    params: dict[str, Any]


class QueuedJobs(JobManager):
    def __init__(self, database: Database, bus: EventBus) -> None:
        super().__init__(database, bus)
        self.queued: list[QueuedJob] = []

    async def submit(
        self,
        kind: JobKind,
        handler: JobHandler,
        params: dict[str, Any] | None = None,
        exclusive_group: str | None = None,
        dedupe_key: str | None = None,
    ) -> str:
        self.queued.append(QueuedJob(kind, handler, dict(params or {})))
        return f"queued-{len(self.queued)}"


def harness_library(database: Database) -> DivineWillLibrary:
    folder = Path(str(database.engine.url.database)).parent
    bus = EventBus()
    jobs = JobManager(database, bus)
    settings = Settings(data_dir=folder / DATA_FOLDER, llm_enabled=False, image_worker_url="")
    host = cast(
        Services,
        LibraryServices(
            database, jobs, RulesService(database), LibraryApplication(Ledger(bus), DiscoveryService(settings)), PlayerRuntime(database, jobs, bus)
        ),
    )

    def player_for(job_id: str) -> PlayerPort:
        return PlanPlayer(host, job_id)

    return DivineWillLibrary(
        artifacts=ArtifactLibrary(database, bus, artifact_ranker(harness_index(database))),
        plans=PlanDesk(database, bus, jobs, player_for, RuleSteps(RuleDesk(host.rules, database, bus, lambda: False))),
        foresight=Foresight(database, bus, QueuedJobs(database, bus), folder / FORECAST_FOLDER),
    )
