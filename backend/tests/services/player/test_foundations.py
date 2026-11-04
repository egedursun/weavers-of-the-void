import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.gods.dedication import dedication_of
from aerona.engine.primitives.holds import ANCHOR_KEY, DEDICATION_KEY, GOLDEN_AGE_KEY, INCITEMENT_KEY, is_held
from aerona.engine.services.war import open_war
from aerona.services.player import catalog, foundations, society
from aerona.services.player.scope import PlayerScope
from tests.engine.warfare.factories import society as give_society
from tests.services.player.factories import PlayerWorld, make_entity, make_son

FOUNDATION_ACTIONS = (
    "war:incite",
    "world:date_golden_age",
    "structure:dedicate",
    "structure:undedicate",
    "son:anchor",
    "son:clear_anchor",
    "foundation:hold",
)


def test_every_foundation_lever_is_in_the_catalog() -> None:
    assert [action for action in FOUNDATION_ACTIONS if action not in catalog.ACTIONS_BY_ID] == []


async def test_a_war_can_be_laid_at_a_gods_feet_held_and_cleared(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Strife", world.world.id)
    first = await make_entity(session, "Red Folk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Blue Folk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    war = await open_war(await scope.context("test"), first, second)
    epoch = await scope.epoch()
    await foundations.set_incitement(scope, foundations.WarIncitement(war_id=war.id, son_id=son.id, hold=True))
    assert war.incited_by_son_id == son.id
    assert await is_held(session, war.event_entity_id, INCITEMENT_KEY, epoch)
    await foundations.hold_foundation(scope, foundations.HoldFoundation(kind=foundations.HoldKind.INCITEMENT, node_id=war.event_entity_id, held=False))
    assert not await is_held(session, war.event_entity_id, INCITEMENT_KEY, epoch)
    with pytest.raises(ValidationFailedError):
        await foundations.hold_foundation(scope, foundations.HoldFoundation(kind=foundations.HoldKind.INCITEMENT, node_id=war.event_entity_id, held=False))
    await foundations.set_incitement(scope, foundations.WarIncitement(war_id=war.id, son_id=None, hold=False))
    assert war.incited_by_son_id is None


async def test_a_golden_age_can_be_dated_and_held(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await give_society(session, town.id)
    with pytest.raises(ValidationFailedError):
        await foundations.set_golden_age_date(scope, foundations.GoldenAgeDate(world_id=world.world.id, since_epoch=0))
    await society.golden_age(scope, society.WorldTarget(world_id=world.world.id))
    epoch = await scope.epoch()
    with pytest.raises(ValidationFailedError):
        await foundations.set_golden_age_date(scope, foundations.GoldenAgeDate(world_id=world.world.id, since_epoch=epoch + 5))
    effect = await foundations.set_golden_age_date(scope, foundations.GoldenAgeDate(world_id=world.world.id, since_epoch=0, hold=True))
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None and row.golden_age_since_epoch == 0
    assert effect.values["communities"] == 1
    assert await is_held(session, world.world.id, GOLDEN_AGE_KEY, epoch)


async def test_dedicating_a_structure_lets_its_god_anchor_there(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Hearth", world.world.id)
    other = await make_son(session, "Ash", world.world.id)
    temple = await make_entity(
        session, "Hearth Temple", EntityType.STRUCTURE, world_id=world.world.id, location_id=world.region.id, stats=StructureStats(splendor=40)
    )
    epoch = await scope.epoch()
    with pytest.raises(ValidationFailedError):
        await foundations.set_anchor(scope, foundations.SonAnchor(son_id=son.id, entity_id=temple.id))
    await foundations.dedicate_structure(scope, foundations.Dedicate(structure_id=temple.id, son_id=son.id, hold=True))
    assert await is_held(session, temple.id, DEDICATION_KEY, epoch)
    await foundations.set_anchor(scope, foundations.SonAnchor(son_id=son.id, entity_id=temple.id, hold=True))
    assert son.anchor_entity_id == temple.id
    assert await is_held(session, son.id, ANCHOR_KEY, epoch)
    await foundations.dedicate_structure(scope, foundations.Dedicate(structure_id=temple.id, son_id=other.id, hold=False))
    dedicated = await dedication_of(session, temple.id)
    assert dedicated is not None and dedicated.id == other.id
    assert son.anchor_entity_id is None
    await foundations.undedicate_structure(scope, foundations.StructureTarget(structure_id=temple.id))
    assert await dedication_of(session, temple.id) is None


async def test_a_god_can_be_cut_loose_from_their_own_creation(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Maker", world.world.id)
    work = await make_entity(session, "First Spring", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id, creator_son_id=son.id)
    await foundations.set_anchor(scope, foundations.SonAnchor(son_id=son.id, entity_id=work.id, hold=False))
    assert son.anchor_entity_id == work.id
    await foundations.clear_anchor(scope, foundations.SonTarget(son_id=son.id))
    assert son.anchor_entity_id is None
    with pytest.raises(ValidationFailedError):
        await foundations.clear_anchor(scope, foundations.SonTarget(son_id=son.id))
