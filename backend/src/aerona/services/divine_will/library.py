from dataclasses import dataclass

from aerona.domain.enums.divine_will import ChunkSource
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.services.container import Services
from aerona.services.divine_will.artifacts import ArtifactLibrary, Ranker
from aerona.services.divine_will.foresight import Foresight
from aerona.services.divine_will.plans import PlanDesk
from aerona.services.divine_will.player import CatalogPlayer
from aerona.services.divine_will.rule_steps import RuleSteps
from aerona.services.rule_changes import rule_desk
from aerona.tools.divine_will.framework import PlayerPort
from aerona.tools.divine_will.retrieval_ports import LoreIndexPort

ARTIFACT_SOURCES = frozenset({ChunkSource.ARTIFACT})


class PlanPlayer(CatalogPlayer):
    def __init__(self, services: Services, job_id: str) -> None:
        super().__init__(services)
        self.job_id = job_id

    def epoch_running(self) -> bool:
        holder = self.services.jobs.busy_group(WORLD_GROUP)
        return holder is not None and holder != self.job_id


@dataclass(frozen=True)
class DivineWillLibrary:
    artifacts: ArtifactLibrary
    plans: PlanDesk
    foresight: Foresight


def artifact_ranker(index: LoreIndexPort) -> Ranker:
    async def ranked(query: str) -> list[int]:
        found = await index.search(query, sources=ARTIFACT_SOURCES, attachments=frozenset())
        ids: list[int] = []
        for hit in found.hits:
            if hit.record.isdigit() and int(hit.record) not in ids:
                ids.append(int(hit.record))
        return ids

    return ranked


def library_for(services: Services, index: LoreIndexPort | None = None) -> DivineWillLibrary:
    def player_for(job_id: str) -> PlayerPort:
        return PlanPlayer(services, job_id)

    return DivineWillLibrary(
        artifacts=ArtifactLibrary(services.database, services.bus, artifact_ranker(index) if index is not None else None),
        plans=PlanDesk(services.database, services.bus, services.jobs, player_for, RuleSteps(rule_desk(services))),
        foresight=Foresight(services.database, services.bus, services.jobs, services.settings.paths.forecasts),
    )
