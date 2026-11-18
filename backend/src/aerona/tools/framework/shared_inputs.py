from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.tool_inputs import BOND_DESCRIPTION_MAX, ETYMOLOGY_MAX, MEANING_MAX, WORD_MAX
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.node import ActorKind
from aerona.language.lexicon import LexiconEntry, admissible_entries
from aerona.tools.framework.inputs import ToolInput


class LinkTarget(StrEnum):
    ENTITY = "entity"
    SON = "son"


class WordKind(StrEnum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    AFFIX = "affix"
    TITLE = "title"
    PLACE_NAME = "place_name"
    PROPER_NAME = "proper_name"
    NUMBER = "number"
    INTERJECTION = "interjection"


class LinkInput(ToolInput):
    target_kind: LinkTarget = LinkTarget.ENTITY
    target_id: int
    kind: BondKind
    description: Annotated[str, Field(max_length=BOND_DESCRIPTION_MAX)] | None = None


class WordInput(ToolInput):
    word: Annotated[str, Field(min_length=1, max_length=WORD_MAX)]
    meaning: Annotated[str, Field(min_length=1, max_length=MEANING_MAX)]
    kind: WordKind | None = None
    origin: Annotated[str, Field(max_length=ETYMOLOGY_MAX)] | None = None
    example: Annotated[str, Field(max_length=ETYMOLOGY_MAX)] | None = None


def part_of_speech(kind: WordKind | None) -> PartOfSpeech:
    if kind is None or kind is WordKind.INTERJECTION:
        return PartOfSpeech.NOUN
    return PartOfSpeech(kind.value)


async def add_words(session: AsyncSession, language: EntityRow, words: Sequence[WordInput], *, actor: tuple[ActorKind, int], epoch: int) -> list[str]:
    entries = [
        LexiconEntry(word=word.word, meaning=word.meaning, part_of_speech=part_of_speech(word.kind), origin=word.origin or "", example=word.example or "")
        for word in words
    ]
    existing = list(await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language.id)))
    admitted = admissible_entries(entries, existing)
    for entry in admitted:
        await add_lexeme(
            session,
            LexemeRow(
                language_entity_id=language.id,
                word=entry.word,
                meaning=entry.meaning,
                part_of_speech=entry.part_of_speech,
                etymology=entry.origin or None,
                example=entry.example or None,
                added_by_kind=actor[0],
                added_by_node_id=actor[1],
                epoch=epoch,
            ),
        )
    await session.flush()
    return [entry.word for entry in admitted]
