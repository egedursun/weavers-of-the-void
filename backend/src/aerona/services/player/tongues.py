from pydantic import Field

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.tongues import LanguagePolicy, ScriptChangeCause, SoundChangeCause, SoundChangeKind, SoundEnvironment, WordRegister
from aerona.engine.tongues import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class LanguageTarget(Command):
    language_id: int


class LanguageEdit(Edited):
    language_id: int


class ChangeDraft(Command):
    language_id: int
    kind: SoundChangeKind
    source: str = Field(min_length=1, max_length=KEY_MAX_LENGTH)
    target: str = Field(default="", max_length=KEY_MAX_LENGTH)
    environment: SoundEnvironment = SoundEnvironment.ANYWHERE


class ChangeEdit(Edited):
    change_id: int


class ChangeTarget(Command):
    change_id: int


class RegisterSet(Command):
    lexeme_id: int
    word_register: WordRegister


class VeilDraft(Command):
    language_id: int
    node_id: int


class ShiftEdit(Edited):
    shift_id: int


class ShiftTarget(Command):
    shift_id: int


class ScriptDraft(Command):
    language_id: int
    system: WritingSystem
    cause: ScriptChangeCause = ScriptChangeCause.INVENTION
    parent_id: int | None = None


class ScriptEdit(Edited):
    script_id: int


class ScriptTarget(Command):
    script_id: int


class ScriptAssign(Command):
    language_id: int
    script_id: int | None = None


class WorkDraft(Command):
    language_id: int
    scholar_id: int | None = None


class PolicyDraft(Command):
    holder_id: int
    language_id: int
    policy: LanguagePolicy
    strength: int = Field(default=50, ge=0, le=SPAN)


class PolicyEdit(Edited):
    holder_id: int
    language_id: int
    policy: LanguagePolicy


class PolicyTarget(Command):
    holder_id: int
    language_id: int
    policy: LanguagePolicy


class TongueChoice(Command):
    god_id: int
    language_id: int | None = None


class TongueEdit(Edited):
    god_id: int


class GodTarget(Command):
    god_id: int


class TongueLesson(Command):
    god_id: int
    mortal_id: int


class PidginDraft(Command):
    first_id: int
    second_id: int


@player_action("sound_change:add", ActionKind.EDIT_RECORD)
async def add_change(scope: PlayerScope, command: ChangeDraft) -> Effect:
    row = await control.decree_change(
        await scope.context("sound_change_add"),
        command.language_id,
        kind=command.kind,
        source=command.source,
        target=command.target,
        environment=command.environment,
        cause=SoundChangeCause.DECREE,
    )
    return Effect("The sound shifts, and every word of the tongue with it.", command.language_id, values={"change_id": row.id})


@player_action("sound_change:edit", ActionKind.EDIT_RECORD)
async def edit_change(scope: PlayerScope, command: ChangeEdit) -> Effect:
    row = await control.edit_change(await scope.context("sound_change_edit"), command.change_id, command.values, command.release)
    return Effect("The sound change is set so; the tongue's words follow it.", row.language_entity_id)


@player_action("sound_change:delete", ActionKind.EDIT_RECORD)
async def delete_change(scope: PlayerScope, command: ChangeTarget) -> Effect:
    language_id = await control.delete_change(await scope.context("sound_change_delete"), command.change_id)
    return Effect("The sound change is undone; the tongue's words go back.", language_id)


@player_action("grammar:edit", ActionKind.EDIT_RECORD)
async def edit_grammar(scope: PlayerScope, command: LanguageEdit) -> Effect:
    await control.edit_grammar(await scope.context("grammar_edit"), command.language_id, command.values, command.release)
    return Effect("The tongue's grammar is set so.", command.language_id)


@player_action("grammar:reset", ActionKind.EDIT_RECORD)
async def reset_grammar(scope: PlayerScope, command: LanguageTarget) -> Effect:
    await control.reset_grammar(await scope.context("grammar_reset"), command.language_id)
    return Effect("The tongue's grammar is drawn anew from its roots.", command.language_id)


@player_action("tongue:edit", ActionKind.EDIT_RECORD)
async def edit_profile(scope: PlayerScope, command: LanguageEdit) -> Effect:
    await control.edit_profile(await scope.context("tongue_edit"), command.language_id, command.values)
    return Effect("The tongue's modality and stage are set so.", command.language_id)


@player_action("word:register", ActionKind.EDIT_RECORD)
async def set_register(scope: PlayerScope, command: RegisterSet) -> Effect:
    row = await control.set_register(await scope.context("word_register"), command.lexeme_id, command.word_register)
    return Effect(f"{row.word} now belongs to the {command.word_register.value} register.", row.language_entity_id)


@player_action("word:veil", ActionKind.EDIT_RECORD)
async def veil_name(scope: PlayerScope, command: VeilDraft) -> Effect:
    row = await control.veil_name(await scope.context("word_veil"), command.language_id, command.node_id)
    return Effect(f"The name is no longer said aloud; folk say {row.word} instead.", command.language_id, values={"lexeme_id": row.id})


@player_action("meaning_shift:edit", ActionKind.EDIT_RECORD)
async def edit_shift(scope: PlayerScope, command: ShiftEdit) -> Effect:
    await control.edit_shift(await scope.context("meaning_shift_edit"), command.shift_id, command.values)
    return Effect("The record of the word's shift is set so.")


@player_action("meaning_shift:delete", ActionKind.EDIT_RECORD)
async def delete_shift(scope: PlayerScope, command: ShiftTarget) -> Effect:
    await control.delete_shift(await scope.context("meaning_shift_delete"), command.shift_id)
    return Effect("The record of the word's shift is struck out.")


@player_action("script:create", ActionKind.EDIT_RECORD)
async def create_script(scope: PlayerScope, command: ScriptDraft) -> Effect:
    row = await control.create_script(await scope.context("script_create"), command.language_id, command.system, command.cause, command.parent_id)
    return Effect(f"{row.name} is written now.", command.language_id, values={"script_id": row.id})


@player_action("script:edit", ActionKind.EDIT_RECORD)
async def edit_script(scope: PlayerScope, command: ScriptEdit) -> Effect:
    row = await control.edit_script(await scope.context("script_edit"), command.script_id, command.values, command.release)
    return Effect(f"{row.name} is set so.", row.origin_language_id)


@player_action("script:delete", ActionKind.EDIT_RECORD)
async def delete_script(scope: PlayerScope, command: ScriptTarget) -> Effect:
    await control.delete_script(await scope.context("script_delete"), command.script_id)
    return Effect("The script is forgotten; the tongues that used it are unwritten now.")


@player_action("script:assign", ActionKind.EDIT_RECORD)
async def assign_script(scope: PlayerScope, command: ScriptAssign) -> Effect:
    await control.assign_script(await scope.context("script_assign"), command.language_id, command.script_id)
    return Effect("The tongue is written in that script now." if command.script_id is not None else "The tongue is unwritten now.", command.language_id)


@player_action("decipherment:start", ActionKind.EDIT_RECORD)
async def start_work(scope: PlayerScope, command: WorkDraft) -> Effect:
    await control.start_work(await scope.context("decipherment_start"), command.language_id, command.scholar_id)
    return Effect("Scholars take up the dead script.", command.language_id)


@player_action("decipherment:edit", ActionKind.EDIT_RECORD)
async def edit_work(scope: PlayerScope, command: LanguageEdit) -> Effect:
    await control.edit_work(await scope.context("decipherment_edit"), command.language_id, command.values, command.release)
    return Effect("The decipherment is set so.", command.language_id)


@player_action("decipherment:delete", ActionKind.EDIT_RECORD)
async def delete_work(scope: PlayerScope, command: LanguageTarget) -> Effect:
    await control.delete_work(await scope.context("decipherment_delete"), command.language_id)
    return Effect("The decipherment is struck from the record.", command.language_id)


@player_action("language_policy:set", ActionKind.EDIT_RECORD)
async def place_policy(scope: PlayerScope, command: PolicyDraft) -> Effect:
    await control.place_policy(await scope.context("language_policy_set"), command.holder_id, command.language_id, command.policy, command.strength)
    return Effect(f"The tongue is {command.policy.value} there now.", command.holder_id)


@player_action("language_policy:edit", ActionKind.EDIT_RECORD)
async def edit_policy(scope: PlayerScope, command: PolicyEdit) -> Effect:
    await control.edit_policy(
        await scope.context("language_policy_edit"), command.holder_id, command.language_id, command.policy, values=command.values, release=command.release
    )
    return Effect("The policy is set so.", command.holder_id)


@player_action("language_policy:delete", ActionKind.EDIT_RECORD)
async def delete_policy(scope: PlayerScope, command: PolicyTarget) -> Effect:
    await control.delete_policy(await scope.context("language_policy_delete"), command.holder_id, command.language_id, command.policy)
    return Effect("The policy is lifted.", command.holder_id)


@player_action("divine_tongue:set", ActionKind.EDIT_RECORD)
async def choose_tongue(scope: PlayerScope, command: TongueChoice) -> Effect:
    row = await control.choose_tongue(await scope.context("divine_tongue_set"), command.god_id, command.language_id)
    return Effect("The god speaks its sacred tongue.", command.god_id, values={"language_id": row.language_entity_id})


@player_action("divine_tongue:edit", ActionKind.EDIT_RECORD)
async def edit_tongue(scope: PlayerScope, command: TongueEdit) -> Effect:
    await control.edit_tongue(await scope.context("divine_tongue_edit"), command.god_id, command.values, command.release)
    return Effect("The god's tongue is set so.", command.god_id)


@player_action("divine_tongue:delete", ActionKind.EDIT_RECORD)
async def delete_tongue(scope: PlayerScope, command: GodTarget) -> Effect:
    await control.delete_tongue(await scope.context("divine_tongue_delete"), command.god_id)
    return Effect("The god no longer has a sacred tongue of its own.", command.god_id)


@player_action("divine_tongue:teach", ActionKind.EDIT_RECORD)
async def teach_tongue(scope: PlayerScope, command: TongueLesson) -> Effect:
    taught = await control.reveal(await scope.context("divine_tongue_teach"), command.god_id, command.mortal_id)
    return Effect("The mortal learns words of the sacred tongue." if taught else "The mortal already knows the tongue.", command.mortal_id)


@player_action("pidgin:make", ActionKind.EDIT_RECORD)
async def make_pidgin(scope: PlayerScope, command: PidginDraft) -> Effect:
    row = await control.found_pidgin(await scope.context("pidgin_make"), command.first_id, command.second_id)
    return Effect(f"{row.name} is spoken between them now.", row.id, values={"language_id": row.id})
