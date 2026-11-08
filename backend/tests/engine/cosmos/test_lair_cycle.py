from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import BeastTemper, SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.models.entity_stats import BeastStats, MortalStats, SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import (
    avenger_target,
    bonded_state,
    deified,
    deify,
    disturbed,
    lair_cycle,
    pick_prey,
    profile_beast,
    rob_hoard,
    slayer_towns,
    towns_near,
)
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, tick, tuned
from tests.engine.cosmos.test_flora_rp2 import land


async def lair(ctx: TickContext, cosmos: Cosmos) -> tuple[EntityRow, EntityRow, BeastProfileRow, EntityRow]:
    region = await make_region(ctx.session, "Fell", cosmos.home.id)
    town = await make_entity(
        ctx.session, "Watch Hold", EntityType.SETTLEMENT, SettlementStats(population=900, defense=20), world_id=cosmos.home.id, location_id=region.id
    )
    beast = await make_entity(
        ctx.session, "Old Horror", EntityType.BEAST, BeastStats(hp=300, danger=60, strength=60), world_id=cosmos.home.id, location_id=region.id
    )
    row = await profile_beast(ctx, beast, None, size=SizeClass.HUGE)
    row.lair_place_id = region.id
    await ctx.session.flush()
    return region, town, row, beast


async def mortal(ctx: TickContext, cosmos: Cosmos, home: EntityRow, name: str) -> EntityRow:
    return await make_entity(ctx.session, name, EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=home.id)


async def test_an_old_beast_dies_of_age_and_a_tamed_one_guards_its_keeper(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    _, town, row, beast = await lair(ctx, cosmos)
    atlas = await RegionAtlas.load(ctx.session)
    row.age, row.lifespan = 200, 100
    assert await lair_cycle(ctx, atlas, beast, row) == "old age"
    row.age = 0
    row.temper, row.bound_to_node_id = BeastTemper.TAMED, town.id
    assert await lair_cycle(ctx, atlas, beast, row) is None
    assert (stat(town, "defense") or 0) > 20


async def test_a_bond_of_taming_tames_the_beast_in_time(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    _, town, row, beast = await lair(ctx, cosmos)
    tamer = await mortal(ctx, cosmos, town, "Ilsa")
    assert await bonded_state(ctx, beast.id) is None
    await connect(ctx.session, tamer.id, beast.id, BondKind.TAMED, ctx.epoch)
    assert await bonded_state(ctx, beast.id) is not None
    row.willpower = 0
    taming = tick(ctx.session, rules)
    await lair_cycle(taming, await RegionAtlas.load(ctx.session), beast, row)
    assert row.temper is BeastTemper.TAMED and row.bound_to_node_id == tamer.id


async def test_a_woken_beast_raids_the_town_near_its_lair(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    _, town, row, beast = await lair(ctx, cosmos)
    atlas = await RegionAtlas.load(ctx.session)
    assert town in await towns_near(ctx, atlas, row)
    waking = tick(ctx.session, tuned(rules, "beasts", wake_chance=100, vengeance_chance=0, slayer_shun_pct=0))
    text = await lair_cycle(waking, atlas, beast, row)
    assert row.woke_epoch == waking.epoch and row.temper in {BeastTemper.HUNGRY, BeastTemper.SLEEPING, BeastTemper.ENRAGED}
    assert text is not None


async def test_digging_war_and_theft_disturb_a_sleeping_beast(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region, town, _, beast = await lair(ctx, cosmos)
    assert not await disturbed(ctx, beast, None)
    assert not await disturbed(ctx, beast, region.id)
    thief = await mortal(ctx, cosmos, town, "Tam")
    await remember(ctx.session, rules, holder_id=beast.id, subject_id=thief.id, kind=MemoryKind.CHEATED_US, magnitude=-30, epoch=ctx.epoch)
    assert await disturbed(ctx, beast, region.id)
    ground = await land(ctx.session, region.id, cosmos.home.id)
    ground.mined = 5
    await ctx.session.flush()
    assert await disturbed(ctx, beast, region.id)


async def test_a_wounded_beast_hunts_the_home_of_its_wounder_and_shuns_slayers(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region, town, _, beast = await lair(ctx, cosmos)
    other = await make_entity(ctx.session, "Far Hold", EntityType.SETTLEMENT, SettlementStats(population=900), world_id=cosmos.home.id, location_id=region.id)
    hunter = await mortal(ctx, cosmos, town, "Bram")
    await remember(ctx.session, rules, holder_id=beast.id, subject_id=hunter.id, kind=MemoryKind.HARMED_ME, magnitude=-40, epoch=ctx.epoch)
    vengeful = tick(ctx.session, tuned(rules, "beasts", vengeance_chance=100))
    assert await avenger_target(vengeful, beast, [other, town]) is town
    slain = await make_entity(ctx.session, "Lesser Horror", EntityType.BEAST, BeastStats(hp=10), world_id=cosmos.home.id, location_id=region.id)
    await connect(ctx.session, hunter.id, slain.id, BondKind.KILLED, ctx.epoch)
    assert town.id in await slayer_towns(ctx)
    shunning = tick(ctx.session, tuned(rules, "beasts", slayer_shun_pct=100))
    assert await pick_prey(shunning, beast, [town], None) is None
    assert await pick_prey(shunning, beast, [town], other) is other


async def test_a_dreaded_beast_comes_to_be_worshipped(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    _, town, row, beast = await lair(ctx, cosmos)
    atlas = await RegionAtlas.load(ctx.session)
    assert await deify(ctx, atlas, beast, row) is None
    set_stats(beast, renown=100, terror=100)
    worship = tick(ctx.session, tuned(rules, "beasts", deify_chance=100))
    assert await deify(worship, atlas, beast, row) is not None
    assert await deified(ctx, beast.id)
    prayers = await ctx.session.scalar(select(BondRow).where(BondRow.source_node_id == town.id, BondRow.kind == BondKind.WORSHIPS))
    assert prayers is not None
    assert await deify(worship, atlas, beast, row) is None


async def test_a_thief_carries_off_part_of_the_hoard(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    _, town, row, beast = await lair(ctx, cosmos)
    thief = await mortal(ctx, cosmos, town, "Tam")
    assert await rob_hoard(ctx, beast, thief) == 0
    row.hoard = {CommodityKind.LUXURIES.value: 100, CommodityKind.TOOLS.value: 100}
    await GoodsLedger(ctx.session, ctx.epoch).add(town.id, CommodityKind.TOOLS, 1, GoodsFlow.PRODUCTION)
    await ctx.session.flush()
    assert await rob_hoard(ctx, beast, thief) > 0
    assert row.hoard[CommodityKind.TOOLS.value] < 100
    assert (await ctx.session.get(BeastProfileRow, beast.id)) is row
