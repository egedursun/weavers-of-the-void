from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import WarSide
from aerona.domain.models.entity_stats import SettlementStats, SpeciesStats
from aerona.engine.phases.ecology import ecology
from aerona.engine.phases.geography import geography
from aerona.engine.phases.remembrance import MemorialForm, commemorate, wars_remembered
from aerona.engine.phases.world_balance import balance_sons, guard_patronless, revive_world, son_shares
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, settlement, son_draft
from tests.engine.cycles.factories import context, flags, tune, war


async def test_ended_war_is_remembered_with_an_epic_and_a_lament(session: AsyncSession, world: CoreWorld) -> None:
    city = await settlement(session, "Dunmoor", world, world.regions[1], prosperity=10)
    row = await war(session, world, world.people, city, ended=9, victor=world.people)
    session.add_all(
        [
            WarSideRow(war_id=row.id, entity_id=side.id, side=side_kind, joined_epoch=1)
            for side, side_kind in ((world.people, WarSide.ATTACKER), (city, WarSide.DEFENDER))
        ]
    )
    await session.flush()
    ctx = context(session, world, tune(Rules(), remembrance={"war_chance": 100, "monument_chance": 0}), 10)
    assert await wars_remembered(ctx, 5) == 1
    memorials = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.ARTWORK).order_by(EntityRow.id)))
    assert [item.subtype for item in memorials] == ["epic", "lament"]
    for item in memorials:
        assert EntityFlag.COMMEMORATION.value in await flags(session, item.id)


async def test_the_god_can_order_a_dead_hero_remembered(session: AsyncSession, world: CoreWorld) -> None:
    hero = await mortal(session, "Bren", world, world.regions[0].id)
    hero.status, hero.end_epoch = EntityStatus.DEAD, 9
    await session.flush()
    created = await commemorate(context(session, world, Rules(), 10), hero.id, MemorialForm.TALE)
    saga = await session.get(EntityRow, created[0])
    assert saga is not None and saga.entity_type is EntityType.LEGEND


async def test_crowded_world_gives_a_son_to_the_needy_one_and_patronless_worlds_get_a_guardian(session: AsyncSession, world: CoreWorld) -> None:
    other, regions = await add_empty_world(session)
    await entity(session, "Orun Folk", EntityType.SETTLEMENT, SettlementStats(population=500), world_id=other.id, location_id=regions[0].id)
    sons = SonRepository(session)
    for name in ("Ves", "Kor"):
        await sons.create(son_draft(name, world.world.id))
    ctx = context(session, world, Rules(), 10)
    shares = {share.world_id: share for share in await son_shares(session, ctx.rules, 10)}
    assert shares[world.world.id].sons == 3 and shares[other.id].share >= 1
    assert await balance_sons(ctx) == 1
    assert await guard_patronless(ctx) == 2
    assert other.patron_son_id is not None


async def test_revive_world_raises_a_faction_and_new_life(session: AsyncSession, world: CoreWorld) -> None:
    ctx = context(session, world, tune(Rules(), world_balance={"faction_population": 100}), 10)
    created = await revive_world(ctx, world.world.id)
    kinds = [(await session.get(EntityRow, record_id)).entity_type for record_id in created]
    assert EntityType.FACTION in kinds and len(created) >= 2


async def test_starved_prey_dies_out_and_its_hunter_is_named(session: AsyncSession, world: CoreWorld) -> None:
    prey = world.species
    prey.stats = prey.stats.model_copy(update={"abundance": 1})
    hunter = await entity(
        session, "Night Wolf", EntityType.SPECIES, SpeciesStats(hp=60, danger=70, abundance=90), world_id=world.world.id, location_id=world.regions[2].id
    )
    await bond(session, hunter.id, prey.id, BondKind.HUNTS)
    await ecology(context(session, world, tune(Rules(), ecology={"noise": 1, "predation": 20}), 10))
    assert prey.status is EntityStatus.DEAD
    assert EntityFlag.EXTINCT.value in await flags(session, prey.id)
    assert stat(hunter, "abundance") is not None


async def test_empty_region_bears_a_place_and_the_crowded_settlement_moves_to_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fernbridge", world, world.regions[1], population=4000)
    await geography(context(session, world, tune(Rules(), geography={"seed_chance": 100, "move_chance": 100, "seed_cap": 4}), 10))
    place = await session.get(EntityRow, town.location_id)
    assert place is not None and place.entity_type is EntityType.PLACE and place.location_id == world.regions[1].id
