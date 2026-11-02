from collections.abc import Collection, Iterable, Sequence

from pydantic import BaseModel, ConfigDict

from aerona.constants.language import LEXICON_TEXT_MAX_LETTERS, LEXICON_WORD_MAX_LETTERS
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.rules.registry import Rules


class LexiconEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str
    meaning: str
    part_of_speech: PartOfSpeech = PartOfSpeech.NOUN
    origin: str = ""
    example: str = ""


class Cognate(BaseModel):
    model_config = ConfigDict(frozen=True)

    first_word: str
    second_word: str
    first_meaning: str
    second_meaning: str


def admissible_entries(entries: Iterable[LexiconEntry], existing_words: Collection[str]) -> list[LexiconEntry]:
    known = {word.strip().casefold() for word in existing_words}
    admitted: list[LexiconEntry] = []
    for entry in entries:
        word = entry.word.strip()[:LEXICON_WORD_MAX_LETTERS]
        meaning = entry.meaning.strip()[:LEXICON_TEXT_MAX_LETTERS]
        if not word or not meaning or word.casefold() in known:
            continue
        known.add(word.casefold())
        admitted.append(
            entry.model_copy(
                update={
                    "word": word,
                    "meaning": meaning,
                    "origin": entry.origin.strip()[:LEXICON_TEXT_MAX_LETTERS],
                    "example": entry.example.strip()[:LEXICON_TEXT_MAX_LETTERS],
                }
            )
        )
    return admitted


def cognates(first: Sequence[LexiconEntry], second: Sequence[LexiconEntry], rules: Rules) -> list[Cognate]:
    settings = rules.language
    root_letters = settings.root_letters
    by_word: dict[str, list[int]] = {}
    by_root: dict[str, list[int]] = {}
    for index, entry in enumerate(second):
        lowered = entry.word.casefold()
        by_word.setdefault(lowered, []).append(index)
        if len(lowered) >= root_letters:
            by_root.setdefault(lowered[:root_letters], []).append(index)
    found: list[Cognate] = []
    for entry in first:
        lowered = entry.word.casefold()
        matches = set(by_word.get(lowered, ()))
        if len(lowered) >= root_letters:
            matches.update(by_root.get(lowered[:root_letters], ()))
        for index in sorted(matches):
            other = second[index]
            found.append(Cognate(first_word=entry.word, second_word=other.word, first_meaning=entry.meaning, second_meaning=other.meaning))
            if len(found) >= settings.max_cognates:
                return found
    return found
