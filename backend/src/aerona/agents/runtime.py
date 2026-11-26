from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ports import LanguageModel, Publish, silent
from aerona.agents.turns.ports import ToolkitFactory
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.domain.enums.providers import ModelRole
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmDisabledError
from aerona.rules.registry import Rules


@dataclass
class AgentRuntime:
    database: Database
    model: LanguageModel
    publish: Publish = silent
    toolkits: ToolkitFactory | None = None
    rules_override: Rules | None = field(default=None)

    @property
    def llm_enabled(self) -> bool:
        return self.model.enabled

    @property
    def world_model(self) -> str:
        return self.model.model_of(ModelRole.WORLD_AGENTS)

    def require_llm(self, what: str) -> None:
        if not self.model.enabled:
            raise LlmDisabledError(f"LLM calls are disabled ({what}).")

    async def rules(self, session: AsyncSession) -> Rules:
        if self.rules_override is not None:
            return self.rules_override
        cosmos = await CosmosRepository(session).require_cosmos()
        return rules_from_snapshot(cosmos.rules_snapshot)

    async def current_rules(self) -> Rules:
        async with self.database.read() as session:
            return await self.rules(session)

    def note(self, text: str, **extra: object) -> None:
        self.publish(EventKind.SYSTEM_NOTE, {"text": text, **extra})

    def error(self, text: str, *, retryable: bool = False, **extra: object) -> None:
        self.publish(EventKind.SYSTEM_ERROR, {"text": text, "will_retry": retryable, **extra})

    def step(self, text: str) -> None:
        self.publish(EventKind.FATE_STEP, {"text": text})
