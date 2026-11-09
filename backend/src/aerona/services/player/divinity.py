from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import CouncilMotion, DivineWoundKind, DomainHook, GodGoalKind, SonPunishment
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.mind import ActKind
from aerona.engine.divine import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Edit = dict[str, int | str | bool | None]


class Edited(Command):
    values: Edit = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class HookSetting(Command):
    world_id: int
    domain: Domain
    hook: DomainHook
    pct: int = 100


class HookTarget(Command):
    world_id: int
    domain: Domain
    hook: DomainHook


class GoalDraft(Command):
    god_id: int
    kind: GodGoalKind
    target_id: int | None = None
    world_id: int | None = None
    domain: Domain | None = None
    amount: int = 0


class GoalEdit(Edited):
    goal_id: int


class GoalTarget(Command):
    goal_id: int


class StandingEdit(Edited):
    community_id: int
    god_id: int


class StandingTarget(Command):
    community_id: int
    god_id: int


class WoundDraft(Command):
    god_id: int
    kind: DivineWoundKind
    severity: int = 50
    domain: Domain | None = None


class WoundEdit(Edited):
    wound_id: int


class WoundTarget(Command):
    wound_id: int


class AvatarDraft(Command):
    god_id: int
    place_id: int


class AvatarEdit(Edited):
    avatar_id: int


class AvatarTarget(Command):
    avatar_id: int


class TabooSetting(Command):
    act: ActKind
    severity: int = 50


class TabooTarget(Command):
    act: ActKind


class AttentionEdit(Edited):
    world_id: int


class AttentionTarget(Command):
    world_id: int


class PactDraft(Command):
    son_id: int
    god_id: int
    epochs: int | None = None


class RulingDraft(Command):
    motion: CouncilMotion
    target_id: int | None = None
    world_id: int | None = None
    school: MagicSchool | None = None
    punishment: SonPunishment | None = None


class RulingEdit(Edited):
    ruling_id: int


class RulingTarget(Command):
    ruling_id: int


class LawEdit(Edited):
    law_id: int


class OuterEdit(Edited):
    being_id: int


class BreachDraft(Command):
    being_id: int
    region_id: int | None = None
    strength: int = 30


class BreachEdit(Edited):
    breach_id: int


class BreachTarget(Command):
    breach_id: int


@player_action("domain_hook:set", ActionKind.EDIT_RECORD)
async def set_hook(scope: PlayerScope, command: HookSetting) -> Effect:
    await control.set_hook(await scope.context("domain_hook_set"), command.world_id, command.domain, command.hook, command.pct)
    return Effect(f"The hook now works at {command.pct}% in that world.", command.world_id)


@player_action("domain_hook:clear", ActionKind.EDIT_RECORD)
async def clear_hook(scope: PlayerScope, command: HookTarget) -> Effect:
    await control.clear_hook(await scope.context("domain_hook_clear"), command.world_id, command.domain, command.hook)
    return Effect("The hook works as it usually does.", command.world_id)


@player_action("god_goal:set", ActionKind.EDIT_RECORD)
async def set_goal(scope: PlayerScope, command: GoalDraft) -> Effect:
    row = await control.set_goal(
        await scope.context("god_goal_set"),
        command.god_id,
        command.kind,
        target_id=command.target_id,
        world_id=command.world_id,
        domain=command.domain,
        amount=command.amount,
    )
    return Effect("The god takes up a new aim.", command.god_id, values={"goal_id": row.id})


@player_action("god_goal:edit", ActionKind.EDIT_RECORD)
async def edit_goal(scope: PlayerScope, command: GoalEdit) -> Effect:
    row = await control.edit_goal(await scope.context("god_goal_edit"), command.goal_id, command.values, command.release)
    return Effect("The aim is reshaped.", row.god_node_id)


@player_action("god_goal:drop", ActionKind.EDIT_RECORD)
async def drop_goal(scope: PlayerScope, command: GoalTarget) -> Effect:
    await control.drop_goal(await scope.context("god_goal_drop"), command.goal_id)
    return Effect("The aim is set aside.")


@player_action("divine_standing:set", ActionKind.EDIT_RECORD)
async def set_standing(scope: PlayerScope, command: StandingEdit) -> Effect:
    await control.set_standing(await scope.context("standing_set"), command.community_id, command.god_id, command.values, command.release)
    return Effect("The people's regard of the god is set.", command.community_id)


@player_action("divine_standing:clear", ActionKind.EDIT_RECORD)
async def clear_standing(scope: PlayerScope, command: StandingTarget) -> Effect:
    await control.clear_standing(await scope.context("standing_clear"), command.community_id, command.god_id)
    return Effect("The people's regard of the god is forgotten.", command.community_id)


@player_action("divine_wound:inflict", ActionKind.EDIT_RECORD)
async def inflict_wound(scope: PlayerScope, command: WoundDraft) -> Effect:
    row = await control.wound_god(await scope.context("divine_wound_inflict"), command.god_id, command.kind, command.severity, command.domain)
    return Effect("The god is wounded.", command.god_id, values={"wound_id": row.id})


@player_action("divine_wound:edit", ActionKind.EDIT_RECORD)
async def edit_wound(scope: PlayerScope, command: WoundEdit) -> Effect:
    row = await control.edit_wound(await scope.context("divine_wound_edit"), command.wound_id, command.values, command.release)
    return Effect("The wound is reshaped.", row.god_node_id)


@player_action("divine_wound:remove", ActionKind.EDIT_RECORD)
async def remove_wound(scope: PlayerScope, command: WoundTarget) -> Effect:
    await control.remove_wound(await scope.context("divine_wound_remove"), command.wound_id)
    return Effect("The wound is gone.")


@player_action("avatar:manifest", ActionKind.CREATE_ENTITY)
async def manifest_avatar(scope: PlayerScope, command: AvatarDraft) -> Effect:
    avatar = await control.manifest_avatar(await scope.context("avatar_manifest"), command.god_id, command.place_id)
    return Effect(f"{avatar.name} walks the world.", avatar.id, created_ids=(avatar.id,))


@player_action("avatar:edit", ActionKind.EDIT_RECORD)
async def edit_avatar(scope: PlayerScope, command: AvatarEdit) -> Effect:
    await control.edit_avatar(await scope.context("avatar_edit"), command.avatar_id, command.values, command.release)
    return Effect("The mortal form is reshaped.", command.avatar_id)


@player_action("avatar:withdraw", ActionKind.EDIT_RECORD)
async def withdraw_avatar(scope: PlayerScope, command: AvatarTarget) -> Effect:
    await control.withdraw_avatar(await scope.context("avatar_withdraw"), command.avatar_id)
    return Effect("The god leaves its mortal form.", command.avatar_id)


@player_action("taboo:set", ActionKind.EDIT_RECORD)
async def set_taboo(scope: PlayerScope, command: TabooSetting) -> Effect:
    await control.set_taboo(await scope.context("taboo_set"), command.act, command.severity)
    return Effect(f"{command.act.value.replace('_', ' ').capitalize()} is taboo to the Creator.")


@player_action("taboo:remove", ActionKind.EDIT_RECORD)
async def remove_taboo(scope: PlayerScope, command: TabooTarget) -> Effect:
    await control.remove_taboo(await scope.context("taboo_remove"), command.act)
    return Effect(f"{command.act.value.replace('_', ' ').capitalize()} is no longer taboo.")


@player_action("attention:set", ActionKind.EDIT_RECORD)
async def set_attention(scope: PlayerScope, command: AttentionEdit) -> Effect:
    await control.set_attention(await scope.context("attention_set"), command.world_id, command.values, command.release)
    return Effect("The Creator's eye on that world is set.", command.world_id)


@player_action("attention:clear", ActionKind.EDIT_RECORD)
async def clear_attention(scope: PlayerScope, command: AttentionTarget) -> Effect:
    await control.clear_attention(await scope.context("attention_clear"), command.world_id)
    return Effect("The Creator's eye on that world starts afresh.", command.world_id)


@player_action("divine_pact:seal", ActionKind.EDIT_RECORD)
async def seal_pact(scope: PlayerScope, command: PactDraft) -> Effect:
    treaty = await control.pact(await scope.context("divine_pact_seal"), command.son_id, command.god_id, command.epochs)
    return Effect(f"{treaty.name} is sealed.", treaty.id, created_ids=(treaty.id,))


@player_action("ruling:decree", ActionKind.EDIT_RECORD)
async def decree(scope: PlayerScope, command: RulingDraft) -> Effect:
    row, lines = await control.decree(
        await scope.context("ruling_decree"),
        command.motion,
        target_id=command.target_id,
        world_id=command.world_id,
        school=command.school,
        punishment=command.punishment,
    )
    return Effect("; ".join(lines) or "The ruling stands.", command.target_id, values={"ruling_id": row.id})


@player_action("ruling:edit", ActionKind.EDIT_RECORD)
async def edit_ruling(scope: PlayerScope, command: RulingEdit) -> Effect:
    await control.edit_ruling(await scope.context("ruling_edit"), command.ruling_id, command.values, command.release)
    return Effect("The ruling is reshaped.")


@player_action("ruling:revoke", ActionKind.EDIT_RECORD)
async def revoke_ruling(scope: PlayerScope, command: RulingTarget) -> Effect:
    await control.revoke_ruling(await scope.context("ruling_revoke"), command.ruling_id)
    return Effect("The ruling is struck out.")


@player_action("law_profile:edit", ActionKind.EDIT_RECORD)
async def edit_law(scope: PlayerScope, command: LawEdit) -> Effect:
    await control.edit_law(await scope.context("law_profile_edit"), command.law_id, command.values, command.release)
    return Effect("The law's working is reshaped.", command.law_id)


@player_action("outer_profile:edit", ActionKind.EDIT_RECORD)
async def edit_outer(scope: PlayerScope, command: OuterEdit) -> Effect:
    await control.edit_outer(await scope.context("outer_profile_edit"), command.being_id, command.values, command.release)
    return Effect("The outer being's nature is reshaped.", command.being_id)


@player_action("breach:open", ActionKind.EDIT_RECORD)
async def open_breach(scope: PlayerScope, command: BreachDraft) -> Effect:
    row = await control.open_breach(await scope.context("breach_open"), command.being_id, command.region_id, command.strength)
    return Effect("A breach opens.", command.being_id, values={"breach_id": row.id})


@player_action("breach:edit", ActionKind.EDIT_RECORD)
async def edit_breach(scope: PlayerScope, command: BreachEdit) -> Effect:
    row = await control.edit_breach(await scope.context("breach_edit"), command.breach_id, command.values, command.release)
    return Effect("The breach is reshaped.", row.outer_entity_id)


@player_action("breach:close", ActionKind.EDIT_RECORD)
async def close_breach(scope: PlayerScope, command: BreachTarget) -> Effect:
    await control.close_breach(await scope.context("breach_close"), command.breach_id)
    return Effect("The breach is sealed.")
