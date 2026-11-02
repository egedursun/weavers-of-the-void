from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import (
    DEFAULT_PROFILE_CONSONANTS,
    DEFAULT_PROFILE_MAX_SYLLABLES,
    DEFAULT_PROFILE_MIN_SYLLABLES,
    DEFAULT_PROFILE_SYLLABLES,
    DEFAULT_PROFILE_VOWELS,
)
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.naming import seed_of

DEFAULT_PHONOLOGY = Phonology(
    vowels=DEFAULT_PROFILE_VOWELS,
    consonants=DEFAULT_PROFILE_CONSONANTS,
    syllable_patterns=DEFAULT_PROFILE_SYLLABLES,
    min_syllables=DEFAULT_PROFILE_MIN_SYLLABLES,
    max_syllables=DEFAULT_PROFILE_MAX_SYLLABLES,
)


async def language_profile(session: AsyncSession, language: EntityRow, parent_id: int | None = None) -> LanguageProfileRow:
    profile = await session.get(LanguageProfileRow, language.id)
    if profile is not None:
        return profile
    parent = await session.get(LanguageProfileRow, parent_id) if parent_id is not None else None
    world = await session.get(WorldRow, language.world_id)
    phonology = parent.phonology if parent is not None else (world.phonology if world is not None and world.phonology is not None else DEFAULT_PHONOLOGY)
    profile = LanguageProfileRow(entity_id=language.id, phonology=phonology, seed=seed_of("language", language.id), parent_language_id=parent_id)
    session.add(profile)
    await session.flush()
    return profile


async def has_script(session: AsyncSession, language_id: int) -> bool:
    profile = await session.get(LanguageProfileRow, language_id)
    return profile is not None and profile.writing_system is not None
