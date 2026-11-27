from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.travel import TravelMethod, VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.context import TickContext
from aerona.engine.military.vessels import (
    SeaTally,
    backfill_vessels,
    batter_fleet,
    best_hull,
    fleet_bonus,
    fresh_profile,
    legend_of,
    owner_of,
    renown_fleet,
    sea_fight,
    seamanship_of,
    strange_waters,
    weather_leg,
    wreck,
)
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.rules.registry import Rules
from tests.db.factories import seed_world
from tests.engine.warfare.factories import bond, make, make_ctx, tune


async def ship(ctx: TickContext, world_id: int, name: str, hull: VehicleFrame = VehicleFrame.WARSHIP, **stats: int) -> tuple[EntityRow, VesselProfileRow]:
    vessel = await make(ctx.session, name, EntityType.VESSEL, world_id, **stats)
    row = fresh_profile(ctx.rules, vessel, hull, owner_id=None, home_port=None)
    row.status = VesselStatus.AFLOAT
    ctx.session.add(row)
    await ctx.session.flush()
    return vessel, row


async def test_a_fresh_ship_takes_its_hull_and_the_best_hull_follows_knowledge(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    _, row = await ship(ctx, world_id, "Gull")
    assert row.frame is VehicleFrame.WARSHIP and row.condition == PERCENT and row.crew > 0
    knowledge = await KnowledgeMap.load(session)
    assert best_hull(knowledge, None, 0) is VehicleFrame.BOAT
    assert best_hull(knowledge, 1, 0) in set(VehicleFrame)
    assert await seamanship_of(ctx, row, knowledge) == 0


async def test_a_storm_batters_a_ship_and_a_wreck_retires_it(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    vessel, row = await ship(ctx, world_id, "Gull")
    tally = SeaTally()
    await weather_leg(ctx, vessel, row, None, tally)
    assert tally.storms == 0
    await weather_leg(ctx, vessel, row, WeatherKind.STORM, tally)
    assert tally.storms == 1 and row.condition < PERCENT and row.renown > 0
    row.condition = 1
    await weather_leg(ctx, vessel, row, WeatherKind.STORM, tally)
    assert row.status is VesselStatus.WRECKED and tally.wrecks == 1 and vessel.status is not EntityStatus.CANON


async def test_a_strange_ship_lost_at_sea_may_sail_on_as_a_ghost(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), seafaring={"ghost_chance": 100}))
    vessel, row = await ship(ctx, world_id, "Wraith", strangeness=100)
    tally = SeaTally()
    await wreck(ctx, vessel, row, "in a storm", tally)
    assert row.status is VesselStatus.GHOST and tally.ghosts == 1


async def test_strange_waters_reveal_hidden_routes_and_renown_makes_a_legend(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    vessel, row = await ship(ctx, world_id, "Wraith", strangeness=100)
    other = await seed_world(session, "Farshore", "Farshore Sun")
    route = RouteRow(world_a_id=world_id, world_b_id=other.id, method=TravelMethod.DEATH_CURRENT, duration_epochs=1, danger=10, known=False, created_epoch=1)
    session.add(route)
    await session.flush()
    tally = SeaTally()
    await strange_waters(ctx, vessel, row, tally)
    assert route.known and tally.routes == 1
    assert await legend_of(ctx, vessel, row, tally) is None
    row.renown = ctx.rules.seafaring.legend_renown
    legend = await legend_of(ctx, vessel, row, tally)
    assert legend is not None and row.legend_entity_id == legend.id
    assert await legend_of(ctx, vessel, row, tally) is None


async def test_ships_fight_at_sea_and_fleets_share_the_battle(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    first = await ship(ctx, world_id, "Gull")
    second = await ship(ctx, world_id, "Raft", VehicleFrame.RAFT)
    tally = SeaTally()
    winner = await sea_fight(ctx, first, second, None, tally)
    assert winner is first[0] and tally.fights == 1 and second[1].condition < PERCENT
    owner = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    await bond(session, owner.id, first[0].id, BondKind.OWNS)
    assert await owner_of(ctx, first[0].id) is owner
    army = await make(session, "Iron Host", EntityType.PEOPLE, world_id, population=10)
    first[1].fleet_army_entity_id = army.id
    await session.flush()
    assert await fleet_bonus(ctx, army.id, None) > 0
    renown = first[1].renown
    await renown_fleet(ctx, army.id)
    assert first[1].renown > renown
    assert await batter_fleet(ctx, army.id, 1.0, region_id=None) == 1
    assert first[1].status is VesselStatus.WRECKED
    assert (await session.scalars(select(VesselProfileRow).where(VesselProfileRow.fleet_army_entity_id == army.id))).first() is not None


async def test_a_hull_with_no_armour_left_is_backfilled_as_broken_not_whole(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    wreckage = await make(session, "Hulk", EntityType.VESSEL, world_id, armor=0, crew=0)
    sound = await make(session, "Gull", EntityType.VESSEL, world_id)
    assert await backfill_vessels(ctx) == 2
    broken = await session.get(VesselProfileRow, wreckage.id)
    whole = await session.get(VesselProfileRow, sound.id)
    assert broken is not None and broken.condition == 0 and broken.crew == 0
    assert whole is not None and whole.condition == PERCENT and whole.crew > 0


async def test_the_backfill_never_resets_a_ship_that_already_has_its_profile(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    built = await make(session, "Long Keel", EntityType.VESSEL, world_id)
    session.add(
        VesselProfileRow(
            entity_id=built.id,
            kind=VehicleKind.SHIP,
            frame=VehicleFrame.GALLEY,
            seaworthiness=91,
            cargo_capacity=77,
            crew=33,
            condition=64,
            locked=["seaworthiness"],
        )
    )
    await session.flush()
    bare = await make(session, "Bare Hull", EntityType.VESSEL, world_id)
    assert await backfill_vessels(ctx) == 1
    kept = await session.get(VesselProfileRow, built.id)
    assert kept is not None
    assert (kept.frame, kept.seaworthiness, kept.cargo_capacity, kept.crew, kept.condition) == (VehicleFrame.GALLEY, 91, 77, 33, 64)
    assert kept.locked == ["seaworthiness"]
    assert await session.get(VesselProfileRow, bare.id) is not None
