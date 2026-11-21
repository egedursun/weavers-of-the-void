from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import ItemStats, StructureStats
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.grave_goods.acts import guard_allowed
from aerona.engine.grave_goods.robbery import GraveTally, legacy_graves, rob, try_graves, unearth_graves
from aerona.engine.lifecycle.mortal_death import after_death
from aerona.engine.lore.items import owner_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import set_stats
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def burying_town(session: AsyncSession, world: CoreWorld, name: str = "Barrowby", treatment: RemainsTreatment = RemainsTreatment.BURIAL) -> EntityRow:
    town = await settlement(session, name, world, world.regions[0])
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    if await session.get(PeopleCultureRow, world.people.id) is None:
        session.add(
            PeopleCultureRow(
                people_entity_id=world.people.id,
                cohesion=50,
                literacy=10,
                urbanisation=10,
                martial_style=MartialStyle.SHIELDWALL,
                inheritance=InheritanceCustom.PRIMOGENITURE,
                remains_treatment=treatment,
                locked=[],
            )
        )
    await session.flush()
    return town


async def treasure(session: AsyncSession, world: CoreWorld, owner: EntityRow, name: str, renown: int) -> EntityRow:
    item = await entity(session, name, EntityType.ITEM, ItemStats(might=20), world_id=world.world.id, location_id=owner.location_id)
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.RING, renown=renown, locked=[]))
    await bond(session, owner.id, item.id, BondKind.OWNS)
    return item


async def buried(session: AsyncSession, world: CoreWorld, town: EntityRow, wealth: int = 80) -> tuple[EntityRow, GraveGoodsRow]:
    ctx = await manual_context(session, "burial", tuned_rules(grave_goods={"share_by_rank_pct": 50, "sealed_value": 100}))
    dead = await mortal(session, "Orm Haldane", world, town.id)
    await shift_points(session, dead, wealth)
    await treasure(session, world, dead, "The Barrow Ring", 90)
    await treasure(session, world, dead, "A Plain Cup", 5)
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    await after_death(ctx, dead)
    row = await session.scalar(select(GraveGoodsRow).where(GraveGoodsRow.dead_entity_id == dead.id))
    assert row is not None
    return dead, row


async def test_the_dead_keep_their_finest_things_and_a_share_of_their_wealth_out_of_the_inheritance(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    heir = await mortal(session, "Ysa Haldane", world, town.id)
    dead, row = await buried(session, world, town)
    del heir
    ring = await session.scalar(select(EntityRow).where(EntityRow.name == "The Barrow Ring"))
    assert ring is not None and row.items == [ring.id] and row.goods_value == 40 and row.custom is RemainsTreatment.BURIAL
    ctx = await manual_context(session, "check", tuned_rules())
    assert await owner_of(ctx, ring.id) == dead.id and await points_of(session, dead) == 40 and row.guard is GraveGuard.NONE
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "dead.goods_placed")) is not None


async def test_a_people_that_burns_its_dead_lays_nothing_in_a_grave(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world, "Pyreford", RemainsTreatment.CREMATION)
    ctx = await manual_context(session, "pyre", tuned_rules())
    dead = await mortal(session, "Cind Pyre", world, town.id)
    await shift_points(session, dead, 50)
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    await after_death(ctx, dead)
    assert await session.scalar(select(GraveGoodsRow.id)) is None


async def test_a_robber_takes_the_goods_and_the_kin_and_people_of_the_dead_hold_it_against_them(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    dead, row = await buried(session, world, town)
    robber = await mortal(session, "Vel Graves", world, town.id)
    ctx = await manual_context(session, "rob", tuned_rules(grave_goods={"rob_chance_per_value_pct": 100}))
    tally = GraveTally()
    await try_graves(ctx, tally)
    assert tally.robbed == 1 and row.robbed_epoch == ctx.epoch and row.robber_node_id == robber.id and row.items == [] and row.goods_value == 0
    assert await points_of(session, robber) == 40
    grudge = await session.scalar(select(MemoryRow).where(MemoryRow.subject_node_id == robber.id, MemoryRow.kind == MemoryKind.DESECRATED_HOLY))
    assert grudge is not None and dead.id != robber.id


async def test_a_watched_grave_catches_its_robber_and_brings_a_case_of_theft(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    _dead, row = await buried(session, world, town)
    robber = await mortal(session, "Kel Snatch", world, town.id)
    row.guard = GraveGuard.GUARDED
    ctx = await manual_context(session, "caught", tuned_rules(grave_goods={"caught_pct": 100}))
    tally = GraveTally()
    assert not await rob(ctx, row, robber, tally)
    assert tally.caught == 1 and row.robbed_epoch is None
    case = await session.scalar(select(CrimeCaseRow).where(CrimeCaseRow.accused_entity_id == robber.id))
    assert case is not None and case.crime is CrimeKind.THEFT


async def test_a_curse_takes_a_robber_only_where_the_land_holds_magic(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    _dead, row = await buried(session, world, town)
    robber = await mortal(session, "Mot Hex", world, town.id)
    ctx = await manual_context(session, "curse", tuned_rules(grave_goods={"curse_pct": 100}))
    set_stats(world.regions[0], magic=0)
    assert not await guard_allowed(ctx, row, GraveGuard.CURSED, town.id)
    set_stats(world.regions[0], magic=100)
    assert await guard_allowed(ctx, row, GraveGuard.CURSED, town.id)
    row.guard = GraveGuard.CURSED
    assert await rob(ctx, row, robber, GraveTally(), sure=True)
    assert await has_flag(session, robber.id, EntityFlag.CURSED)


async def test_a_dig_finds_an_untouched_grave_its_goods_and_an_account_of_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    dead, row = await buried(session, world, town)
    digger = await mortal(session, "Ana Spade", world, town.id)
    ctx = await manual_context(session, "dig", tuned_rules())
    assert await unearth_graves(ctx, [town.id], digger) == 1
    assert row.found_epoch == ctx.epoch and row.finder_node_id == digger.id and await points_of(session, digger) == 40
    account = await session.scalar(select(AccountRow).where(AccountRow.subject_node_id == dead.id))
    assert account is not None and account.fidelity == ctx.rules.grave_goods.find_fidelity


async def test_the_notable_dead_of_old_worlds_buried_where_a_tomb_stands_gain_their_goods_once(session: AsyncSession, world: CoreWorld) -> None:
    town = await burying_town(session, world)
    tomb = await entity(session, "The Old Barrow", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=tomb.id, kind=StructureKind.TOMB, host_entity_id=town.id, locked=[]))
    ancient = await mortal(session, "Old King Brann", world, town.id)
    await shift_points(session, ancient, 60)
    ancient.status, ancient.end_epoch = EntityStatus.DEAD, 0
    await session.flush()
    ctx = await manual_context(session, "legacy", tuned_rules())
    tally = GraveTally()
    await legacy_graves(ctx, tally)
    await legacy_graves(ctx, tally)
    row = await session.scalar(select(GraveGoodsRow).where(GraveGoodsRow.dead_entity_id == ancient.id))
    assert tally.legacy == 1 and row is not None and row.grave_entity_id == tomb.id and row.goods_value > 0
