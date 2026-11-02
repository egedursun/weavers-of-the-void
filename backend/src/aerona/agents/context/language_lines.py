from collections import defaultdict

from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.random import SeededRandom
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import LanguageLine, LanguageLinesContext
from aerona.prompts.contexts.common import LexiconWord

LEXICON_STREAM = "context.lexicon"


async def speakers_of(scope: Scope, language_ids: list[int]) -> dict[int, list[EntityRow]]:
    rows = await scope.session.execute(
        select(BondRow.target_node_id, EntityRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(language_ids))
    )
    found: dict[int, list[EntityRow]] = defaultdict(list)
    for language_id, speaker in rows:
        found[language_id].append(speaker)
    return found


async def near_languages(scope: Scope, son: SonRow, speakers: dict[int, list[EntityRow]]) -> set[int]:
    worshippers = set(
        await scope.session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == son.id)
        )
    )
    near = set()
    for language_id, people in speakers.items():
        if any(person.creator_son_id == son.id or person.id in worshippers for person in people):
            near.add(language_id)
    return near


async def language_lines(scope: Scope, world_id: int | None, son: SonRow | None = None) -> str:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    languages = list(await scope.session.scalars(statement))
    if not languages:
        return ""
    ids = [language.id for language in languages]
    lexemes: dict[int, list[LexemeRow]] = defaultdict(list)
    for lexeme in await scope.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id.in_(ids)).order_by(LexemeRow.id)):
        lexemes[lexeme.language_entity_id].append(lexeme)
    speakers = await speakers_of(scope, ids)
    context = scope.rules.context
    base = context.son_words_per_language if son is not None else context.fate_words_per_language
    near = await near_languages(scope, son, speakers) if son is not None else set()
    lines = []
    for language in languages:
        if son is None:
            count = base
        elif language.id in near or language.creator_son_id == son.id:
            count = base + context.near_language_extra_words
        else:
            count = max(context.far_language_min_words, base - context.far_language_fewer_words)
        words = lexemes[language.id]
        rng = SeededRandom.for_epoch(scope.cosmos.rng_seed, scope.epoch, f"{LEXICON_STREAM}.{language.id}")
        sample = sorted(rng.sample(words, min(count, len(words))), key=lambda word: word.id) if words else []
        living = [person.name for person in speakers[language.id] if person.status is EntityStatus.CANON]
        lines.append(
            LanguageLine(
                id=language.id,
                name=language.name,
                subtype=language.subtype,
                word_count=len(words),
                speakers=living,
                dead=not living,
                words=[LexiconWord(word=word.word, meaning=word.meaning, kind=word.part_of_speech.value if word.part_of_speech else None) for word in sample],
            )
        )
    return render(PromptId.LANGUAGE_LINES, LanguageLinesContext(languages=lines))
