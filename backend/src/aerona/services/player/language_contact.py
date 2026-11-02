from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.language_contact import order_creole, run_language_contact
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class CommunityTarget(Command):
    community_id: int


class Empty(Command):
    pass


@player_action("language:creole", ActionKind.BIRTH_CREOLE)
async def creole(scope: PlayerScope, command: CommunityTarget) -> Effect:
    language = await order_creole(scope.session, scope.rules, command.community_id)
    return Effect(f"A new tongue was born: {language.name}.", language.id, created_ids=(language.id,))


@player_action("language:contact_run", ActionKind.OTHER)
async def run_now(scope: PlayerScope, command: Empty) -> Effect:
    await run_language_contact(scope.session, scope.rules)
    return Effect("Tongues met along roads, borders and markets.")
