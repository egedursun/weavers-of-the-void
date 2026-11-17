from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import PeopleStats
from aerona.epoch.phases.distribution import donor_ok, godless_moves, patronless_moves, protected, worship_count, worshipped_here
from tests.engine.core.factories import CoreWorld, bond, entity, tuned_rules
from tests.engine.cosmos.factories import make_region, make_world
from tests.engine.society.factories import son as make_son

RULES = tuned_rules(god_hand={"dispatch_donor_min_sons": 1, "assignment_protection_epochs": 3}, empty_world={"dispatch_wait_epochs": 0})


async def test_a_son_turns_to_a_world_with_a_people_but_no_god(session: AsyncSession, world: CoreWorld) -> None:
    far = await make_world(session, "Far Shore")
    folk = await entity(session, "Shore Folk", EntityType.PEOPLE, PeopleStats(population=800), world_id=far.id)
    assert folk.id
    son = world.son
    son.current_world_id = world.world.id
    moves = await patronless_moves(session, RULES, 5, [son], [world.world, far])
    assert [(move.son.id, move.world.id) for move in moves] == [(son.id, far.id)]
    assert "has a people but no god" in moves[0].detail and son.current_world_id == far.id


async def test_an_empty_world_with_land_draws_a_son_to_bring_life_there(session: AsyncSession, world: CoreWorld) -> None:
    empty = await make_world(session, "Bare Rock")
    await make_region(session, "Bare Plain", empty.id, fertility=10)
    son = world.son
    son.current_world_id = world.world.id
    moves = await patronless_moves(session, RULES, 5, [son], [empty])
    assert moves and "where nobody lives" in moves[0].detail and "bring life there" in moves[0].detail


async def test_a_chained_protected_or_lone_son_stays(session: AsyncSession, world: CoreWorld) -> None:
    far = await make_world(session, "Far Shore")
    await entity(session, "Shore Folk", EntityType.PEOPLE, PeopleStats(population=800), world_id=far.id)
    son = world.son
    son.current_world_id = world.world.id
    son.manually_assigned_epoch = 4
    assert protected(RULES, son, 5) and not protected(RULES, son, 9)
    assert await patronless_moves(session, RULES, 5, [son], [far]) == []
    son.manually_assigned_epoch = None
    assert not donor_ok(tuned_rules(god_hand={"dispatch_donor_min_sons": 2}), son, [son])


async def test_worship_is_counted_per_world_and_a_worshipped_world_needs_no_son(session: AsyncSession, world: CoreWorld) -> None:
    son = world.son
    await bond(session, world.people.id, son.id, BondKind.WORSHIPS)
    assert await worship_count(session, son, world.world.id) == 1
    assert await worshipped_here(session, world.world.id, {son.id})
    other = await make_son(session, "Velm", world.world.id)
    assert not await worshipped_here(session, world.world.id, {other.id})


async def test_a_godless_inhabited_world_takes_the_least_worshipped_son(session: AsyncSession, world: CoreWorld) -> None:
    far = await make_world(session, "Far Shore")
    await entity(session, "Shore Folk", EntityType.PEOPLE, PeopleStats(population=800), world_id=far.id)
    busy, idle = world.son, await make_son(session, "Velm", world.world.id)
    busy.current_world_id = idle.current_world_id = world.world.id
    await bond(session, world.people.id, busy.id, BondKind.WORSHIPS)
    moves = await godless_moves(session, RULES, 5, [busy, idle], [world.world, far])
    assert [(move.son.id, move.world.id) for move in moves] == [(idle.id, far.id)]
