from aerona.agents.context.naming import world_naming
from aerona.agents.context.scope import Scope
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import DialectBlockContext


def dialect_block(scope: Scope) -> str:
    if not scope.multi_world:
        return ""
    fallback = scope.primary_world.phonology if scope.primary_world is not None else None
    return render(PromptId.DIALECT_BLOCK, DialectBlockContext(worlds=[world_naming(world, fallback) for world in scope.living_worlds]))
