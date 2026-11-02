import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository, edit_distance_within_one, normalize_name, roman
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.names import NameSimilarityPolicy
from tests.db.factories import make_entity, make_son, seed_world

POLICY = NameSimilarityPolicy(similar_max_length=7, family_cap=3, root_letters=4)


def test_normalization_folds_case_accents_and_spacing() -> None:
    assert normalize_name("  Élan   Vir ") == "elan vir"
    assert normalize_name("ORVAEL") == normalize_name("orvael")


def test_roman_numerals() -> None:
    assert [roman(number) for number in (2, 3, 4, 9, 14, 40, 1994)] == ["II", "III", "IV", "IX", "XIV", "XL", "MCMXCIV"]
    assert roman(0) == "0"


def test_edit_distance_within_one() -> None:
    assert edit_distance_within_one("lemir", "lesir")
    assert edit_distance_within_one("lemir", "lemirs")
    assert not edit_distance_within_one("lemir", "losur")


async def test_names_are_unique_across_node_kinds(session: AsyncSession, world_id: int) -> None:
    await make_son(session, "Karun", world_id)
    with pytest.raises(ConflictError):
        await make_entity(session, "karun", EntityType.REGION, world_id=world_id)
    with pytest.raises(ConflictError):
        await seed_world(session, name="KARUN", star_name="Another Sun")


async def test_unique_name_appends_roman_numerals(session: AsyncSession, world_id: int) -> None:
    names = NameRepository(session)
    await make_entity(session, "Ash Tower", EntityType.PLACE, location_id=(await make_entity(session, "Duna", EntityType.REGION, world_id=world_id)).id)
    assert await names.unique_name("Ash Tower") == "Ash Tower II"
    await make_entity(session, "Ash Tower II", EntityType.REGION, world_id=world_id)
    assert await names.unique_name("Ash Tower") == "Ash Tower III"
    assert await names.unique_name("Fresh Name") == "Fresh Name"


async def test_similar_single_word_names_are_detected(session: AsyncSession, world_id: int) -> None:
    names = NameRepository(session)
    await make_entity(session, "Lemir", EntityType.REGION, world_id=world_id)
    assert await names.similar_name("Lesir", POLICY) == "Lemir"
    assert await names.similar_name("Lesir Vale", POLICY) is None
    assert await names.similar_name("Kodrun", POLICY) is None


async def test_name_families_are_capped(session: AsyncSession, world_id: int) -> None:
    names = NameRepository(session)
    for name in ("Lenmiras", "Lenmasir", "Lenmurek"):
        await make_entity(session, name, EntityType.REGION, world_id=world_id)
    assert await names.similar_name("Lenmoravi", POLICY) is None
    assert await names.similar_name("Lenmoravi", POLICY, family=True) == "Lenmasir"


async def test_rejection_releases_and_restoration_reclaims_the_name(session: AsyncSession, world_id: int) -> None:
    repository = EntityRepository(session)
    names = NameRepository(session)
    region = await make_entity(session, "Sorvan", EntityType.REGION, world_id=world_id)
    await repository.set_status(region, EntityStatus.REJECTED, epoch=2)
    assert not await names.is_taken("Sorvan")
    await repository.set_status(region, EntityStatus.CANON, epoch=3)
    assert await names.owner("Sorvan") == region.id


async def test_restoration_fails_when_the_name_was_taken_meanwhile(session: AsyncSession, world_id: int) -> None:
    repository = EntityRepository(session)
    region = await make_entity(session, "Tamur", EntityType.REGION, world_id=world_id)
    await repository.set_status(region, EntityStatus.REJECTED, epoch=2)
    await make_son(session, "Tamur", world_id)
    with pytest.raises(ConflictError):
        await repository.set_status(region, EntityStatus.CANON, epoch=3)


async def test_rename_moves_the_registry_entry(session: AsyncSession, world_id: int) -> None:
    names = NameRepository(session)
    region = await make_entity(session, "Velun", EntityType.REGION, world_id=world_id)
    await EntityRepository(session).rename(region, "Velunar")
    assert region.name == "Velunar"
    assert await names.owner("Velunar") == region.id
    assert await names.owner("Velun") is None
