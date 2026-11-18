from collections import Counter

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.naming import naming_item
from aerona.agents.context.scope import load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow, lexeme_key
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.language.syllables import syllabify
from aerona.prompts import PromptId
from aerona.prompts.contexts.common import LexiconWord
from aerona.prompts.contexts.council import TranslateContext
from aerona.prompts.schemas.council import NewWordOutput, TranslationOutput


def common_syllables(words: list[str], limit: int) -> list[str]:
    first: Counter[str] = Counter()
    last: Counter[str] = Counter()
    for word in words:
        parts = syllabify(word.casefold())
        if parts:
            first[parts[0]] += 1
            last[parts[-1]] += 1
    return [item for item, _ in first.most_common(limit)] + [item for item, _ in last.most_common(limit)]


async def translate(runtime: AgentRuntime, language_id: int, text: str) -> TranslationOutput:
    runtime.require_llm("translation")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        language = await session.get(EntityRow, language_id)
        if language is None or language.entity_type is not EntityType.LANGUAGE:
            raise NotFoundError("No such language.")
        original = text.strip()[: rules.council.translate_max_chars]
        if not original:
            raise ValidationFailedError("Write something to translate.")
        lexicon = list(
            await session.scalars(
                select(LexemeRow).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id).limit(rules.council.translate_lexicon_words)
            )
        )
        profile = await session.get(LanguageProfileRow, language.id)
        world = scope.worlds.get(language.world_id)
        context = TranslateContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            language_name=language.name,
            language_subtype=language.subtype,
            language_description=language.description,
            naming_rule=naming_item(profile.phonology if profile is not None else world.phonology if world is not None else None),
            syllables=common_syllables([word.word for word in lexicon], rules.council.translate_syllables),
            lexicon=[LexiconWord(word=word.word, meaning=word.meaning) for word in lexicon],
            text=original,
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.TRANSLATION,
        system=(PromptId.TRANSLATE_SYSTEM, context),
        user=(PromptId.TRANSLATE_USER, context),
        output=TranslationOutput,
        time_limit=rules.council.translate_timeout,
    )
    async with runtime.database.write() as session:
        known = {lexeme_key(word) for word in await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language_id))}
        epoch = (await load_scope(session, rules)).epoch
        added: list[NewWordOutput] = []
        for word in output.new_words:
            key = lexeme_key(word.word)
            if not key or key in known or len(added) >= rules.council.translate_new_words_max:
                continue
            known.add(key)
            added.append(word)
            await add_lexeme(
                session,
                LexemeRow(
                    language_entity_id=language_id,
                    word=word.word.strip(),
                    meaning=word.meaning.strip(),
                    part_of_speech=word.kind,
                    etymology=word.origin.strip() or None,
                    example=f'"{output.translation}" ({original})',
                    added_by_kind=ActorKind.CREATOR,
                    added_by_node_id=scope.creator.id,
                    epoch=epoch,
                ),
            )
    runtime.publish(EventKind.TRANSLATED, {"language_id": language_id, "new_words": len(added)})
    return output.model_copy(update={"new_words": added})
