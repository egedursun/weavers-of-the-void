from dataclasses import fields

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule_meta
from aerona.rules.registry import Rules

TIMEOUTS = frozenset({("model", "structured_timeout"), ("model", "agent_timeout")})


def budget_floors() -> dict[tuple[str, str], float]:
    defaults = Rules()
    floors: dict[tuple[str, str], float] = {}
    for namespace in fields(defaults):
        for definition in fields(type(getattr(defaults, namespace.name))):
            meta = rule_meta(definition)
            if meta.group == RuleGroup.CONTEXT_BUDGETS or (namespace.name, definition.name) in TIMEOUTS:
                floors[(namespace.name, definition.name)] = float(meta.default)
    return floors


async def raise_context_budgets(session: AsyncSession, rules: Rules, epoch: int) -> int:
    del rules, epoch
    cosmos = await CosmosRepository(session).get()
    if cosmos is None or not cosmos.rules_snapshot:
        return 0
    snapshot = cosmos.rules_snapshot
    raised = 0
    for (namespace, name), floor in budget_floors().items():
        values = snapshot.get(namespace)
        if values is not None and name in values and float(values[name]) < floor:
            values[name] = floor
            raised += 1
    if raised:
        flag_modified(cosmos, "rules_snapshot")
        await session.flush()
    return raised
