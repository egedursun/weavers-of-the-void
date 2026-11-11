from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import LanguageProfileRow
from aerona.domain.models.phonology import Phonology
from aerona.language.alphabet import is_vowel


def nearest(letter: str, inventory: list[str]) -> str:
    return min(inventory, key=lambda item: (abs(ord(item[0]) - ord(letter)), item)) if inventory else letter


def adapt(word: str, phonology: Phonology) -> str:
    vowels = sorted({item.casefold() for item in phonology.vowels if len(item) == 1})
    consonants = sorted({item.casefold() for item in phonology.consonants if len(item) == 1})
    known = set(vowels) | set(consonants)
    built: list[str] = []
    for letter in word.casefold():
        if not letter.isalpha() or letter in known or not known:
            built.append(letter)
        elif is_vowel(letter):
            built.append(nearest(letter, vowels))
        else:
            built.append(nearest(letter, consonants))
    result = "".join(built)
    return result[0].upper() + result[1:] if result and word[:1].isupper() else result


async def adapted(session: AsyncSession, word: str, borrower_id: int) -> str:
    profile = await session.get(LanguageProfileRow, borrower_id)
    return adapt(word, profile.phonology) if profile is not None else word
