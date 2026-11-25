from dataclasses import dataclass, field

from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.epoch.orchestrator import EpochOrchestrator
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.services.application import ApplicationServices
from aerona.services.genesis_wizard import GenesisWizard
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.rules import RulesService
from aerona.services.team.state import TeamState
from aerona.settings import Settings


@dataclass
class Services:
    settings: Settings
    database: Database
    bus: EventBus
    jobs: JobManager
    rules: RulesService
    application: ApplicationServices
    orchestrator: EpochOrchestrator
    player: PlayerRuntime
    stop_requests: set[str] = field(default_factory=set)
    team: TeamState = field(default_factory=TeamState)

    @property
    def agents(self) -> AgentRuntime:
        return self.application.agents

    def genesis(self) -> GenesisWizard:
        return GenesisWizard(self.database, self.rules.current, self.application.ports, self.bus)
