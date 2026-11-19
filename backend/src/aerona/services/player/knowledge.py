from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.knowledge_levels import run_knowledge_levels, set_knowledge_level
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.services.world import spend_essence


class KnowledgeLevel(Command):
    knowledge_id: int
    deepen: bool = True


class Empty(Command):
    pass


@player_action("knowledge:level", ActionKind.SET_KNOWLEDGE_LEVEL)
async def change_level(scope: PlayerScope, command: KnowledgeLevel) -> Effect:
    spent = 0
    if command.deepen:
        spent = await spend_essence(scope.session, scope.rules.knowledge.creator_deepen_cost, "knowledge.creator_deepen_cost")
    change = await set_knowledge_level(scope.session, scope.rules, command.knowledge_id, 1 if command.deepen else -1)
    verb = "deepened" if command.deepen else "blunted"
    return Effect(
        f"{change.knowledge.name} was {verb}; it now stands at level {change.level}.", change.knowledge.id, essence_spent=spent, values={"level": change.level}
    )


@player_action("knowledge:run", ActionKind.OTHER)
async def run_now(scope: PlayerScope, command: Empty) -> Effect:
    await run_knowledge_levels(scope.session, scope.rules)
    return Effect("The scholars and clerks of the world worked on their knowledge.")
