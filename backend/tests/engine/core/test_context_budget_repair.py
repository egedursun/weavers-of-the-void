from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot, snapshot_rules
from aerona.rules.registry import Rules
from aerona.services.integrity.context_budgets import raise_context_budgets
from tests.engine.core.factories import CoreWorld


async def test_a_stored_world_takes_the_larger_context_budgets_and_keeps_any_it_set_larger_itself(session: AsyncSession, world: CoreWorld) -> None:
    del world
    cosmos = await CosmosRepository(session).require_cosmos()
    stored = snapshot_rules(Rules())
    stored["context"]["son_prompt_chars"] = 24000.0
    stored["context"]["son_summary_chars"] = 14000.0
    stored["model"]["agent_timeout"] = 420.0
    stored["context"]["son_memory_chars"] = 99000.0
    cosmos.rules_snapshot = stored
    await session.flush()
    assert await raise_context_budgets(session, Rules(), 1) == 3
    rules = rules_from_snapshot(cosmos.rules_snapshot)
    assert rules.context.son_prompt_chars == Rules().context.son_prompt_chars
    assert rules.context.son_summary_chars == Rules().context.son_summary_chars
    assert rules.model.agent_timeout == Rules().model.agent_timeout
    assert rules.context.son_memory_chars == 99000
    assert await raise_context_budgets(session, Rules(), 1) == 0
