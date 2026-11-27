import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository, split_epithet
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.models.entity_stats import PlaceStats, RegionStats
from tests.db.factories import make_entity, make_son, seed_world


def test_epithet_split() -> None:
    assert split_epithet("Varun, the Drowned King") == ("Varun", "the Drowned King")
    assert split_epithet("Old Varun, the Drowned") == ("Old Varun, the Drowned", None)
    assert split_epithet("Varun, X") == ("Varun, X", None)


async def test_title_is_split_from_the_name(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Morrow, the Grey Shelf", EntityType.REGION, world_id=world_id)
    assert (region.name, region.title) == ("Morrow", "the Grey Shelf")


async def test_world_is_inherited_from_location_then_son(session: AsyncSession, world_id: int) -> None:
    other = await seed_world(session, name="Second Sky", star_name="Second Sun")
    region = await make_entity(session, "Far Shelf", EntityType.REGION, world_id=other.id)
    place = await make_entity(session, "Far Well", EntityType.PLACE, location_id=region.id)
    assert place.world_id == other.id
    son = await make_son(session, "Wandrel", other.id)
    tradition = await make_entity(session, "Far Rite", EntityType.TRADITION, creator_son_id=son.id, origin=EntityOrigin.SON)
    assert tradition.world_id == other.id
    orphan = await make_entity(session, "First Rite", EntityType.TRADITION)
    assert orphan.world_id == world_id


async def test_son_creations_start_unjudged(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Judgen", world_id)
    tradition = await make_entity(session, "Rite of Salt", EntityType.TRADITION, creator_son_id=son.id, origin=EntityOrigin.SON)
    verdict = await EntityRepository(session).verdict(tradition.id)
    assert verdict is not None
    assert verdict.verdict is Verdict.UNJUDGED


async def test_containment_rules_are_enforced(session: AsyncSession, world_id: int) -> None:
    tradition = await make_entity(session, "Ember Rite", EntityType.TRADITION, world_id=world_id)
    with pytest.raises(ValidationFailedError):
        await make_entity(session, "Rite Well", EntityType.PLACE, location_id=tradition.id)


async def test_location_cycles_are_rejected(session: AsyncSession, world_id: int) -> None:
    outer = await make_entity(session, "Outer Reach", EntityType.REGION, world_id=world_id)
    inner = await make_entity(session, "Inner Reach", EntityType.REGION, location_id=outer.id)
    with pytest.raises(ValidationFailedError):
        await EntityRepository(session).move(outer, inner.id, epoch=2)


async def test_stats_must_match_the_type(session: AsyncSession, world_id: int) -> None:
    with pytest.raises(ValidationFailedError):
        await EntityRepository(session).create(
            EntityDraft(
                name="Mismatch",
                entity_type=EntityType.PLACE,
                description="A place with region stats.",
                stats=RegionStats(),
                power_level=1,
                origin=EntityOrigin.ENGINE,
                birth_epoch=1,
                world_id=world_id,
            )
        )


async def test_engine_kind_must_belong_to_the_type(session: AsyncSession, world_id: int) -> None:
    with pytest.raises(ValidationFailedError):
        await EntityRepository(session).create(
            EntityDraft(
                name="Wrong Temple",
                entity_type=EntityType.PLACE,
                description="A place pretending to be a temple.",
                stats=PlaceStats(),
                power_level=1,
                origin=EntityOrigin.ENGINE,
                birth_epoch=1,
                world_id=world_id,
                engine_kind=EngineKind.TEMPLE,
            )
        )


async def test_rejection_hides_bonds_and_moves_contents(session: AsyncSession, world_id: int) -> None:
    repository = EntityRepository(session)
    bonds = BondRepository(session)
    region = await make_entity(session, "Basin", EntityType.REGION, world_id=world_id)
    place = await make_entity(session, "Doomed Grove", EntityType.PLACE, location_id=region.id)
    settlement = await make_entity(session, "Grove Town", EntityType.SETTLEMENT, location_id=place.id)
    neighbour = await make_entity(session, "Neighbour Grove", EntityType.PLACE, location_id=region.id)
    related = await bonds.connect(BondDraft(place.id, neighbour.id, BondKind.RELATED, 1))
    await repository.set_status(place, EntityStatus.REJECTED, epoch=2, fate_note="Fate rejected it.")
    assert related.state is BondState.HIDDEN_REJECTED
    assert settlement.location_id == region.id
    assert await bonds.exists_between(settlement.id, region.id, BondKind.INSIDE)
    await repository.set_status(place, EntityStatus.CANON, epoch=3)
    assert BondState(related.state) is BondState.ACTIVE


async def test_death_records_the_end_epoch(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Ashen", EntityType.REGION, world_id=world_id)
    mortal = await make_entity(session, "Corwen", EntityType.MORTAL, location_id=region.id)
    await EntityRepository(session).set_status(mortal, EntityStatus.DEAD, epoch=5)
    assert mortal.end_epoch == 5


async def test_flags_and_tags(session: AsyncSession, world_id: int) -> None:
    repository = EntityRepository(session)
    region = await make_entity(session, "Marsh", EntityType.REGION, world_id=world_id)
    assert await repository.add_flag(region.id, EntityFlag.CURSED, epoch=2)
    assert not await repository.add_flag(region.id, EntityFlag.CURSED, epoch=3)
    assert await repository.flags(region.id) == {EntityFlag.CURSED}
    assert [row.id for row in await repository.with_flag(EntityFlag.CURSED)] == [region.id]
    assert await repository.remove_flag(region.id, EntityFlag.CURSED)
    assert await repository.add_tags(region.id, ["Salt", "salt", " ash "]) == ["salt", "ash"]
