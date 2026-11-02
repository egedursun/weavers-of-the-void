from pydantic import Field

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.phonology import LanguageSignature
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.epoch.phases.transition import add_epoch_words
from aerona.language.alphabet import fold_word, is_consonant
from aerona.services.player import guards
from aerona.services.player.chronicle import hand
from aerona.services.player.lines import EPOCH_WORDS_ADDED, LANGUAGE_EDITED, SIGNATURE_REDRAWN, WORDS_ADDED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.tools.framework.shared_inputs import WordInput, add_words

SAMPLE_NAMES_MAX = 50
SAMPLE_NAME_LENGTH_MAX = 60
ALPHABET_LENGTH_MAX = 64
WORDS_PER_ORDER_MAX = 50


class EditLanguage(Command):
    language_id: int
    writing_system: WritingSystem | None = None
    clear_writing_system: bool = False
    sample_names: list[str] | None = Field(default=None, max_length=SAMPLE_NAMES_MAX)
    alphabet: str | None = Field(default=None, max_length=ALPHABET_LENGTH_MAX)
    signature: LanguageSignature | None = None
    clear_signature: bool = False


class LanguageTarget(Command):
    language_id: int


class AddWords(Command):
    language_id: int
    words: list[WordInput] = Field(min_length=1, max_length=WORDS_PER_ORDER_MAX)


class EpochWords(Command):
    epoch: int | None = None


async def _language(scope: PlayerScope, language_id: int) -> EntityRow:
    language = await guards.entity(scope.session, language_id)
    return guards.of_types(language, (EntityType.LANGUAGE,), "Only a language has a voice.")


def _checked_signature(signature: LanguageSignature) -> LanguageSignature:
    if not signature.consonants or not all(is_consonant(character) for character in signature.consonants):
        raise ValidationFailedError("A language signature needs consonant letters only.")
    return signature


@player_action("language:edit", ActionKind.EDIT_LANGUAGE)
async def edit_language(scope: PlayerScope, command: EditLanguage) -> Effect:
    language = await _language(scope, command.language_id)
    profile = await language_profile(scope.session, language)
    epoch = await scope.epoch()
    fields: list[str] = []
    if command.clear_writing_system:
        profile.writing_system = None
        profile.script_epoch = None
        fields.append("script cleared")
    elif command.writing_system is not None:
        profile.writing_system = command.writing_system
        profile.script_epoch = epoch
        fields.append(f"script {command.writing_system.value.replace('_', ' ')}")
    if command.sample_names is not None:
        names = tuple(name.strip()[:SAMPLE_NAME_LENGTH_MAX] for name in command.sample_names if name.strip())
        profile.phonology = profile.phonology.model_copy(update={"sample_names": names})
        fields.append(f"{len(names)} sample names")
    if command.alphabet is not None:
        letters = "".join(dict.fromkeys(fold_word(command.alphabet.strip())))
        profile.alphabet = letters or None
        fields.append("alphabet" if letters else "alphabet cleared")
    if command.clear_signature:
        profile.signature = None
        fields.append("signature cleared")
    elif command.signature is not None:
        profile.signature = _checked_signature(command.signature)
        fields.append("signature")
    if not fields:
        raise ValidationFailedError(f"Nothing to change on {language.name}.")
    ctx = await scope.context("edit_language")
    message = await hand(ctx, await scope.creator(), LANGUAGE_EDITED, ids=[language.id], language=language.name, fields=", ".join(fields))
    return Effect(message, language.id)


@player_action("language:signature", ActionKind.REGENERATE_SIGNATURE)
async def regenerate_signature(scope: PlayerScope, command: LanguageTarget) -> Effect:
    language = await _language(scope, command.language_id)
    profile = await language_profile(scope.session, language)
    epoch = await scope.epoch()
    signature = await Namer(scope.session, scope.rules, persist=False).regenerate_signature(language, seed_of(epoch, profile.seed))
    if signature is None:
        raise ValidationFailedError(f"{language.name} has too few sounds to carry a signature.")
    profile.signature = signature
    ctx = await scope.context("language_signature")
    message = await hand(ctx, await scope.creator(), SIGNATURE_REDRAWN, ids=[language.id], language=language.name)
    return Effect(message, language.id, values={"consonants": signature.consonants, "ending": signature.ending})


@player_action("language:epoch_words", ActionKind.ADD_EPOCH_WORDS)
async def run_epoch_words(scope: PlayerScope, command: EpochWords) -> Effect:
    current = await scope.epoch()
    count = await add_epoch_words(scope.session, scope.rules, command.epoch or current)
    ctx = await scope.context("epoch_words")
    message = await hand(ctx, await scope.creator(), EPOCH_WORDS_ADDED, count=count)
    return Effect(message, values={"words": count})


@player_action("language:words", ActionKind.EDIT_LANGUAGE)
async def add_lexicon_words(scope: PlayerScope, command: AddWords) -> Effect:
    language = await _language(scope, command.language_id)
    creator = await scope.creator()
    added = await add_words(scope.session, language, command.words, actor=(ActorKind.CREATOR, creator.id), epoch=await scope.epoch())
    if not added:
        raise ValidationFailedError(f"{language.name} already knows these words, or they carry no meaning.")
    ctx = await scope.context("add_words")
    message = await hand(ctx, creator, WORDS_ADDED, ids=[language.id], language=language.name, words=", ".join(added))
    return Effect(message, language.id, values={"added": len(added), "skipped": len(command.words) - len(added)})
