from sqlalchemy import select, update

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.tongues import (
    DECIPHER_FIELDS,
    DIVINE_TONGUE_FIELDS,
    GRAMMAR_FIELDS,
    POLICY_FIELDS,
    SCRIPT_FIELDS,
    SOUND_CHANGE_FIELDS,
    DecipherWorkRow,
    DivineTongueRow,
    LanguageGrammarRow,
    LanguagePolicyRow,
    MeaningShiftRow,
    ScriptRow,
    SoundChangeRow,
)
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.tongues import (
    LanguageModality,
    LanguagePolicy,
    LanguageStage,
    ScriptChangeCause,
    SoundChangeCause,
    SoundChangeKind,
    SoundEnvironment,
    WordRegister,
)
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found, node
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.queries import add_flag, has_flag
from aerona.engine.tongues.decipher import work_on
from aerona.engine.tongues.divine import give_tongue, teach
from aerona.engine.tongues.grammar import grammar_of
from aerona.engine.tongues.meaning import veil
from aerona.engine.tongues.pidgins import make_pidgin
from aerona.engine.tongues.policy import HOLDER_TYPES, set_policy
from aerona.engine.tongues.scripts import record_script
from aerona.engine.tongues.sounds import Change, add_change, changes_of, rederive

PROFILE_FIELDS = ("modality", "stage")


async def language(ctx: TickContext, language_id: int) -> EntityRow:
    row = await entity(ctx, language_id, "language")
    if row.entity_type is not EntityType.LANGUAGE:
        raise ValidationFailedError(f"{row.name} is not a language.")
    return row


async def decree_change(
    ctx: TickContext, language_id: int, *, kind: SoundChangeKind, source: str, target: str, environment: SoundEnvironment, cause: SoundChangeCause
) -> SoundChangeRow:
    tongue = await language(ctx, language_id)
    if not source.strip():
        raise ValidationFailedError("A sound change needs the sound it changes.")
    row = await add_change(ctx, tongue.id, Change(kind, source.strip().casefold(), target.strip().casefold(), environment), cause)
    await rederive(ctx, tongue.id)
    return row


async def edit_change(ctx: TickContext, change_id: int, values: Values, release: list[str]) -> SoundChangeRow:
    row = apply(await found(ctx, SoundChangeRow, change_id, "sound change"), allowed(values, SOUND_CHANGE_FIELDS, "sound change"), release)
    await ctx.session.flush()
    await rederive(ctx, row.language_entity_id)
    return row


async def delete_change(ctx: TickContext, change_id: int) -> int:
    row = await found(ctx, SoundChangeRow, change_id, "sound change")
    language_id = row.language_entity_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    for index, rest in enumerate(await changes_of(ctx, language_id)):
        rest.position = index
    await rederive(ctx, language_id)
    return language_id


async def edit_grammar(ctx: TickContext, language_id: int, values: Values, release: list[str]) -> LanguageGrammarRow:
    tongue = await language(ctx, language_id)
    row = await grammar_of(ctx.session, tongue.id, ctx.epoch)
    if row is None:
        raise ValidationFailedError(f"{tongue.name} has no grammar to set.")
    apply(row, allowed(values, GRAMMAR_FIELDS, "grammar"), release)
    await ctx.session.flush()
    return row


async def reset_grammar(ctx: TickContext, language_id: int) -> LanguageGrammarRow:
    tongue = await language(ctx, language_id)
    current = await ctx.session.get(LanguageGrammarRow, tongue.id)
    if current is not None:
        await ctx.session.delete(current)
        await ctx.session.flush()
    row = await grammar_of(ctx.session, tongue.id, ctx.epoch)
    if row is None:
        raise ValidationFailedError(f"{tongue.name} has no grammar to draw.")
    return row


async def edit_profile(ctx: TickContext, language_id: int, values: Values) -> LanguageProfileRow:
    tongue = await language(ctx, language_id)
    profile = await language_profile(ctx.session, tongue)
    for key, value in allowed(values, PROFILE_FIELDS, "tongue").items():
        if key == "modality":
            profile.modality = LanguageModality(str(value))
        else:
            profile.stage = LanguageStage(str(value))
    await ctx.session.flush()
    return profile


async def set_register(ctx: TickContext, lexeme_id: int, register: WordRegister) -> LexemeRow:
    row = await found(ctx, LexemeRow, lexeme_id, "word")
    row.register = register
    await ctx.session.flush()
    return row


async def veil_name(ctx: TickContext, language_id: int, node_id: int) -> LexemeRow:
    tongue = await language(ctx, language_id)
    named = await node(ctx, node_id, "thing")
    target = await ctx.session.get(EntityRow, named.id)
    son = await ctx.session.get(SonRow, named.id)
    name = target.name if target is not None else son.name if son is not None else None
    if name is None:
        raise ValidationFailedError("Only a named thing can have its name veiled.")
    row = await veil(ctx, tongue, named.id, name)
    if row is None:
        raise ValidationFailedError(f"{tongue.name} has too few words to make a euphemism.")
    return row


async def edit_shift(ctx: TickContext, shift_id: int, values: Values) -> MeaningShiftRow:
    row = await found(ctx, MeaningShiftRow, shift_id, "meaning shift")
    for key, value in allowed(values, ("old_meaning", "new_meaning"), "meaning shift").items():
        setattr(row, key, str(value))
    await ctx.session.flush()
    return row


async def delete_shift(ctx: TickContext, shift_id: int) -> None:
    await ctx.session.delete(await found(ctx, MeaningShiftRow, shift_id, "meaning shift"))
    await ctx.session.flush()


async def create_script(ctx: TickContext, language_id: int, system: WritingSystem, cause: ScriptChangeCause, parent_id: int | None) -> ScriptRow:
    tongue = await language(ctx, language_id)
    parent = await found(ctx, ScriptRow, parent_id, "script") if parent_id is not None else None
    return await record_script(ctx, tongue, await language_profile(ctx.session, tongue), system, cause=cause, parent=parent)


async def edit_script(ctx: TickContext, script_id: int, values: Values, release: list[str]) -> ScriptRow:
    row = apply(await found(ctx, ScriptRow, script_id, "script"), allowed(values, SCRIPT_FIELDS, "script"), release)
    if row.parent_script_id == row.id:
        raise ValidationFailedError("A script cannot descend from itself.")
    await ctx.session.execute(update(LanguageProfileRow).where(LanguageProfileRow.script_id == row.id).values(writing_system=row.system))
    await ctx.session.flush()
    return row


async def delete_script(ctx: TickContext, script_id: int) -> None:
    row = await found(ctx, ScriptRow, script_id, "script")
    await ctx.session.execute(update(LanguageProfileRow).where(LanguageProfileRow.script_id == row.id).values(script_id=None, writing_system=None))
    await ctx.session.delete(row)
    await ctx.session.flush()


async def assign_script(ctx: TickContext, language_id: int, script_id: int | None) -> LanguageProfileRow:
    tongue = await language(ctx, language_id)
    profile = await language_profile(ctx.session, tongue)
    script = await found(ctx, ScriptRow, script_id, "script") if script_id is not None else None
    profile.script_id = script.id if script is not None else None
    profile.writing_system = script.system if script is not None else None
    profile.script_epoch = ctx.epoch if script is not None else None
    await ctx.session.flush()
    return profile


async def start_work(ctx: TickContext, language_id: int, scholar_id: int | None) -> DecipherWorkRow:
    tongue = await language(ctx, language_id)
    if scholar_id is not None and (await entity(ctx, scholar_id, "scholar")).entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can decipher a script.")
    if not await has_flag(ctx.session, tongue.id, EntityFlag.DECIPHERABLE):
        await add_flag(ctx.session, tongue.id, EntityFlag.DECIPHERABLE, ctx.epoch)
    row = await work_on(ctx, tongue)
    if scholar_id is not None:
        row.scholar_entity_id = scholar_id
    await ctx.session.flush()
    return row


async def edit_work(ctx: TickContext, language_id: int, values: Values, release: list[str]) -> DecipherWorkRow:
    row = apply(await found(ctx, DecipherWorkRow, language_id, "decipherment"), allowed(values, DECIPHER_FIELDS, "decipherment"), release)
    await ctx.session.flush()
    return row


async def delete_work(ctx: TickContext, language_id: int) -> None:
    await ctx.session.delete(await found(ctx, DecipherWorkRow, language_id, "decipherment"))
    await ctx.session.flush()


async def place_policy(ctx: TickContext, holder_id: int, language_id: int, policy: LanguagePolicy, strength: int) -> LanguagePolicyRow:
    holder = await entity(ctx, holder_id, "holder")
    if holder.entity_type not in HOLDER_TYPES:
        raise ValidationFailedError(f"{holder.name} cannot hold a policy on tongues.")
    tongue = await language(ctx, language_id)
    return await set_policy(ctx, holder.id, tongue.id, policy, strength)


async def edit_policy(ctx: TickContext, holder_id: int, language_id: int, policy: LanguagePolicy, *, values: Values, release: list[str]) -> LanguagePolicyRow:
    row = await found(ctx, LanguagePolicyRow, (holder_id, language_id, policy), "language policy")
    apply(row, allowed(values, POLICY_FIELDS, "language policy"), release)
    await ctx.session.flush()
    return row


async def delete_policy(ctx: TickContext, holder_id: int, language_id: int, policy: LanguagePolicy) -> None:
    await ctx.session.delete(await found(ctx, LanguagePolicyRow, (holder_id, language_id, policy), "language policy"))
    await ctx.session.flush()


async def choose_tongue(ctx: TickContext, god_id: int, language_id: int | None) -> DivineTongueRow:
    god = await node(ctx, god_id, "god")
    if language_id is None:
        son = await ctx.session.get(SonRow, god.id)
        if son is None:
            raise ValidationFailedError("Only a son is given a tongue by the world; name a language for any other god.")
        given = await give_tongue(ctx, son)
        if given is None:
            raise ValidationFailedError("No tongue could be given.")
        return given
    tongue = await language(ctx, language_id)
    taken = await ctx.session.scalar(select(DivineTongueRow).where(DivineTongueRow.language_entity_id == tongue.id, DivineTongueRow.god_node_id != god.id))
    if taken is not None:
        raise ValidationFailedError(f"{tongue.name} is already the tongue of another god.")
    row = await ctx.session.get(DivineTongueRow, god.id)
    if row is None:
        row = DivineTongueRow(god_node_id=god.id, language_entity_id=tongue.id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, allowed({"language_entity_id": tongue.id}, DIVINE_TONGUE_FIELDS, "divine tongue"), [])
    (await language_profile(ctx.session, tongue)).stage = LanguageStage.DIVINE
    await ctx.session.flush()
    return row


async def edit_tongue(ctx: TickContext, god_id: int, values: Values, release: list[str]) -> DivineTongueRow:
    row = apply(await found(ctx, DivineTongueRow, god_id, "divine tongue"), allowed(values, DIVINE_TONGUE_FIELDS, "divine tongue"), release)
    await ctx.session.flush()
    return row


async def delete_tongue(ctx: TickContext, god_id: int) -> None:
    await ctx.session.delete(await found(ctx, DivineTongueRow, god_id, "divine tongue"))
    await ctx.session.flush()


async def reveal(ctx: TickContext, god_id: int, mortal_id: int) -> bool:
    mortal = await entity(ctx, mortal_id, "mortal")
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can learn a divine tongue.")
    if await ctx.session.get(DivineTongueRow, god_id) is None:
        raise ValidationFailedError("This god has no tongue to teach yet.")
    return await teach(ctx, god_id, mortal)


async def found_pidgin(ctx: TickContext, first_id: int, second_id: int) -> EntityRow:
    first, second = await entity(ctx, first_id, "community"), await entity(ctx, second_id, "community")
    if first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES or first.id == second.id:
        raise ValidationFailedError("A pidgin is made between two different communities.")
    made = await make_pidgin(ctx, first, second)
    if made is None:
        raise ValidationFailedError("Both communities need a tongue of their own, and not the same one.")
    return made
