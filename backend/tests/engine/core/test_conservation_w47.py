from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.made import ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.powers import PowerSourceRow, SourceDensityRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.cosmography import RiftWork
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.made import RealmAwareness, RealmEntry, RealmPurpose, ReplicatorScale, ReplicatorStage
from aerona.domain.enums.minds import MindSeat, MindUpkeep, StateMedium
from aerona.domain.enums.powers import SourceLocus, SourceRenewal
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, TravelMethod
from aerona.engine.cosmos.rift_control import collect_tolls
from aerona.engine.economy.purse import coin_of
from aerona.engine.industry.energy import draw
from aerona.engine.made.control import RealmDraft, make_realm
from aerona.engine.made.realms import end_realm, enter_realm, minds_inside
from aerona.engine.made.replicators import spread
from aerona.engine.minds.continuity import copy_mind, divide_mind, restore_mind, save_mind
from aerona.engine.powers.sources import convert, renew
from aerona.engine.primitives.distance import RegionAtlas
from tests.db.factories import seed_world
from tests.engine.core.factories import CoreWorld, mortal, settlement
from tests.engine.core.test_agrarian_w23 import realm
from tests.engine.core.test_minds_w44 import at


async def count(session: AsyncSession, column: object) -> int:
    return int(await session.scalar(select(func.count()).select_from(column)) or 0)


async def test_a_rift_toll_moves_coin_from_the_crosser_to_the_keeper_and_nothing_more(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    near, far = await settlement(session, "Hollin", world, world.regions[0]), await settlement(session, "Marrow", world, world.regions[0])
    keeper, crosser = await realm(session, world, [near], None), await realm(session, world, [far], None)
    other = await seed_world(session, name="Lumen", star_name="Lumen Star")
    route = RouteRow(world_a_id=world.world.id, world_b_id=other.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=10, created_epoch=1)
    session.add(route)
    await session.flush()
    toll = ctx.rules.taxation.wealth_per_treasury * 2
    assert await collect_tolls(ctx, route.id, keeper.id, toll) == 0
    session.add(
        JourneyRow(
            traveller_entity_id=crosser.id,
            route_id=route.id,
            origin_world_id=world.world.id,
            destination_world_id=other.id,
            intent=JourneyIntent.TRADE,
            epochs_left=1,
            start_epoch=2,
            status=JourneyStatus.UNDERWAY,
        )
    )
    await session.flush()
    before = await coin_of(session, ctx.rules, keeper) + await coin_of(session, ctx.rules, crosser)
    assert await collect_tolls(ctx, route.id, keeper.id, toll) == toll
    assert await coin_of(session, ctx.rules, keeper) + await coin_of(session, ctx.rules, crosser) == before
    assert RiftWork.GATE in RiftWork and RiftRow.__tablename__ == "rifts"


async def test_copying_and_dividing_a_mind_each_make_exactly_one_mind(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    source = await mortal(session, "Fenn", world, world.regions[0].id)
    await copy_mind(ctx, source.id, MindSeat.BODY, None, forced=True)
    minds = await count(session, MindProfileRow)
    await copy_mind(ctx, source.id, MindSeat.BODY, None, forced=True)
    assert await count(session, MindProfileRow) == minds + 1
    await divide_mind(ctx, source.id, MindSeat.BODY, None)
    assert await count(session, MindProfileRow) == minds + 2


def test_energy_drawn_never_exceeds_what_a_community_has() -> None:
    row = CommunityIndustryRow(community_node_id=1, electric=30, spent={}, short={})
    book = SimpleNamespace(industry={1: row}, magic_heat_pct=0)
    first = draw(book, 1, EnergyKind.ELECTRIC, 20)
    second = draw(book, 1, EnergyKind.ELECTRIC, 20)
    assert (first, second) == (20, 10)
    assert row.spent["electric"] == row.electric
    assert row.short["electric"] == 40 - row.electric


async def test_replicators_that_spread_carry_their_mass_with_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    line = ReplicatorLineRow(name="Grey Line", scale=ReplicatorScale.MINUTE, stage=ReplicatorStage.SPREADING, locked=[])
    session.add(line)
    await session.flush()
    presence = ReplicatorPresenceRow(line_id=line.id, place_node_id=world.regions[0].id, mass=120, growth=10, locked=[])
    session.add(presence)
    await session.flush()
    atlas = await RegionAtlas.load(session)
    seeded = await spread(ctx, atlas, line, presence, here={world.regions[0].id}, towns={})
    await session.flush()
    total = await session.scalar(select(func.sum(ReplicatorPresenceRow.mass)).where(ReplicatorPresenceRow.line_id == line.id))
    assert seeded >= 1
    assert total == 120


async def test_sources_converted_keep_their_density_and_renewal_stops_at_the_base(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    first = PowerSourceRow(name="First Well", drawn_from=SourceLocus.PLACE, renewal=SourceRenewal.REST, locked=[])
    second = PowerSourceRow(name="Second Well", drawn_from=SourceLocus.PLACE, renewal=SourceRenewal.REST, locked=[])
    session.add_all([first, second])
    await session.flush()
    region = world.regions[0].id
    taken = SourceDensityRow(region_entity_id=region, source_id=first.id, density=40, base_density=60, locked=[])
    given = SourceDensityRow(region_entity_id=region, source_id=second.id, density=50, base_density=50, locked=[])
    session.add_all([taken, given])
    await session.flush()
    await convert(ctx, first.id, second.id, region, 80)
    assert taken.density + given.density == 90
    await renew(ctx, taken, first)
    await renew(ctx, taken, first)
    assert taken.density <= taken.base_density


async def test_a_realm_holds_minds_without_making_or_ending_any(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    dweller = await mortal(session, "Gale", world, world.regions[0].id)
    made = await make_realm(
        ctx,
        RealmDraft(
            name="The Still Hall",
            keeper_id=None,
            host_id=None,
            purpose=RealmPurpose.DWELLING,
            time_ratio_pct=100,
            entry=RealmEntry.INTERFACE,
            aware=RealmAwareness.KNOWS,
            upkeep=MindUpkeep.NONE,
        ),
    )
    await enter_realm(ctx, dweller.id, made.dimension_id)
    minds = await count(session, MindProfileRow)
    assert [mind.node_id for mind in await minds_inside(ctx, made)] == [dweller.id]
    await end_realm(ctx, made)
    assert await minds_inside(ctx, made) == []
    assert await count(session, MindProfileRow) == minds


async def test_a_saved_state_is_kept_when_it_is_restored(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    saved = await mortal(session, "Hale", world, world.regions[0].id)
    state = await save_mind(ctx, saved.id, None, None, StateMedium.RECORD, forced=True)
    states = await count(session, MindStateRow)
    saved.status, saved.end_epoch = EntityStatus.DEAD, 3
    await session.flush()
    await restore_mind(ctx, state.id, MindSeat.BODY, None)
    assert await count(session, MindStateRow) == states
    assert saved.status is EntityStatus.CANON
