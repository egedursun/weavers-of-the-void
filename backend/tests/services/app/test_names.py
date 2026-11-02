import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.renames import name_in_text, rename_everywhere
from aerona.rules.registry import Rules
from aerona.services import names
from tests.services.app.factories import Cosmos, make_entity


def test_name_in_text_protects_longer_names_and_numbered_successors() -> None:
    text = "Ash Tower fell. Ash Tower Guards fled. Ash Tower II stood."
    assert name_in_text(text, "Ash Tower", "Cinder Spire", ["Ash Tower Guards"]) == "Cinder Spire fell. Ash Tower Guards fled. Ash Tower II stood."


def test_roman_numerals() -> None:
    assert names.roman_numeral(3) == "III"
    assert names.roman_numeral(1999) == "MCMXCIX"


async def test_unique_and_similar_names(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    assert await names.is_taken(session, "velari folk")
    assert await names.unique_name(session, "Velari Folk") == "Velari Folk II"
    await make_entity(session, "Lemir", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    assert await names.similar_name(session, rules, "Lesir") == "Lemir"
    with pytest.raises(ConflictError):
        await names.validate_new_name(session, rules, "Lesir")
    for name in ("Lenmas", "Lenmur", "Lenmox"):
        await make_entity(session, name, EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    assert await names.similar_name(session, rules, "Lenmiraz", family=True) == "Lenmas"


async def test_rename_everywhere_updates_texts(session: AsyncSession, world: Cosmos) -> None:
    guards = await make_entity(session, "Amberreach Guards", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await ChronicleRepository(session).append(
        ChronicleDraft(epoch=1, kind=ChronicleKind.WORLD, text="Rain fell on Amberreach while Amberreach Guards watched.")
    )
    await ChronicleRepository(session).append(ChronicleDraft(epoch=2, kind=ChronicleKind.WORLD, text="Amberreach slept."))
    world.people.description = "They live in Amberreach."
    result = await rename_everywhere(session, world.region.id, "Goldreach", from_epoch=2)
    assert result.old == "Amberreach"
    assert result.new == "Goldreach"
    assert world.region.name == "Goldreach"
    assert world.people.description == "They live in Goldreach."
    assert guards.name == "Amberreach Guards"
    rows = await ChronicleRepository(session).recent(10)
    assert [row.text for row in rows] == ["Rain fell on Amberreach while Amberreach Guards watched.", "Goldreach slept."]
    assert not await names.is_taken(session, "Amberreach")


async def test_epithet_split_and_named_records(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ora = await make_entity(session, "Ora, the Salt Witch", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    assert await names.apply_epithet(session, ora)
    assert ora.name == "Ora"
    assert ora.title == "the Salt Witch"
    found = await names.find_named_records(session, rules, "The Velari Folk crossed Amberreachian fields near Amberreach.", limit=5)
    assert [row.name for row in found] == ["Velari Folk", "Amberreach"]
    none = await names.find_named_records(session, rules, "Amberreachian roads.")
    assert none == []
