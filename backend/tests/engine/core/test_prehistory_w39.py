from collections import Counter
from collections.abc import Callable

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, object_mapper

from aerona.db.profile_guard import owned_shape, owner_ids
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.prehistory import DeepTimeEventRow, DeepTimeRunRow, PrehistoryEventRow, PrehistoryRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryKind, PrehistorySource, PrehistoryState
from aerona.domain.enums.world import Discovery, WorldType
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.prehistory import run as prerun
from aerona.engine.prehistory.control import abort, configure, open_run
from aerona.engine.prehistory.deep_time import fast_forward
from aerona.engine.prehistory.digest import backfill_world, dreams_of, prehistory_of
from aerona.engine.prehistory.run import born_prehistories, epoch_points, growth_phases, round_phases, run_prehistory
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity
from tests.engine.core.stirring import eager, stir
from tests.engine.core.test_god_control import origin, table_of, tied_to_a_node
from tests.engine.integration.factories import seed_rich_cosmos


async def world_of_kind(database: Database, name: str, world_type: WorldType, *, son_id: int | None = None) -> int:
    async with database.write() as session:
        home = await session.get(WorldRow, (await CosmosRepository(session).require_cosmos()).primary_world_id)
        assert home is not None
        world = await WorldRepository(session).create_world(
            WorldDraft(
                name=name,
                world_type=world_type,
                orbit=home.orbit + 5,
                terrain_seed=name.lower(),
                terrain_sea=0.4,
                terrain_mountains=0.3,
                terrain_humidity=0.5,
                danger=10,
                created_epoch=1,
                star_id=home.star_id,
                creator_son_id=son_id,
            )
        )
        return world.id


async def test_a_prehistory_runs_its_world_while_every_other_world_is_held_and_stamps_the_birth_epoch(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        target = cosmos.frontiers[0].world.id
        home_id = cosmos.home.world.id
        before = {
            row.id: (row.status, row.location_id, dict(row.stats.model_dump()) if row.stats is not None else None)
            for row in await session.scalars(select(EntityRow).where(EntityRow.world_id == home_id))
        }
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        lines = int(await session.scalar(select(func.max(ChronicleRow.id))) or 0)
        newest = int(await session.scalar(select(func.max(EntityRow.id))) or 0)
        ctx = await manual_context(session, "test_prehistory", Rules())
        await configure(ctx, target, 2, 1)
    summary = await run_prehistory(database, target)
    assert summary.state is PrehistoryState.DONE and summary.rounds == 2
    async with database.read() as session:
        row = await session.get(PrehistoryRow, target)
        assert row is not None and row.rounds_done == 2 and row.state is PrehistoryState.DONE and row.birth_epoch == epoch
        assert (await CosmosRepository(session).require_cosmos()).epoch == epoch
        after = {
            row.id: (row.status, row.location_id, dict(row.stats.model_dump()) if row.stats is not None else None)
            for row in await session.scalars(select(EntityRow).where(EntityRow.world_id == home_id))
        }
        assert {key: value for key, value in after.items() if key in before} == before
        stamped = set(await session.scalars(select(ChronicleRow.epoch).where(ChronicleRow.id > lines)))
        assert stamped <= {epoch}
        elsewhere = set(await session.scalars(select(ChronicleRow.world_id).where(ChronicleRow.id > lines, ChronicleRow.world_id.is_not(None))))
        assert elsewhere <= {target}
        born_elsewhere = await session.scalar(
            select(func.count()).select_from(EntityRow).where(EntityRow.id > newest, EntityRow.world_id.is_not(None), EntityRow.world_id != target)
        )
        assert born_elsewhere == 0
        kept = int(await session.scalar(select(func.count()).select_from(PrehistoryEventRow).where(PrehistoryEventRow.world_id == target)) or 0)
        assert kept <= Rules().prehistory.digest_size


async def test_a_stopped_prehistory_keeps_its_rounds_and_runs_on_from_where_it_stopped(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        target = cosmos.frontiers[1].world.id
        ctx = await manual_context(session, "test_prehistory", Rules())
        row = await configure(ctx, target, 2, 2)
        row.state, row.rounds_done = PrehistoryState.RUNNING, 1
        await session.flush()
        await abort(ctx, target)
    stopped = await run_prehistory(database, target)
    assert stopped.rounds == 1 and stopped.state is PrehistoryState.DONE
    assert [phase.name for phase in round_phases(1, 2)] != [phase.name for phase in round_phases(0, 2)]
    assert "world_lives" in [phase.name for phase in growth_phases(PrehistoryKind.LIVING)]
    tables = {table.name for table, _, _ in epoch_points()}
    assert {"settlement_history", "market_prices", "trait_history", "map_snapshots"} <= tables and "epoch_stats" not in tables


async def test_a_mirror_without_a_twin_is_born_as_a_pair_and_a_ship_without_a_source_takes_a_lost_origin(database: Database) -> None:
    async with database.write() as session:
        await seed_rich_cosmos(session)
    mirror = await world_of_kind(database, "Glassmere", WorldType.MIRROR)
    ship = await world_of_kind(database, "Long Voyage", WorldType.GENERATION_SHIP)
    async with database.write() as session:
        ctx = await manual_context(session, "test_prehistory", Rules())
        for world_id in (mirror, ship):
            await configure(ctx, world_id, 1, 1)
    await run_prehistory(database, mirror)
    await run_prehistory(database, ship)
    async with database.read() as session:
        mirrored = await session.get(WorldRow, mirror)
        assert mirrored is not None and mirrored.mirror_twin_id is not None
        twin_row = await session.get(PrehistoryRow, mirrored.mirror_twin_id)
        assert twin_row is not None and twin_row.state is PrehistoryState.DONE
        mirror_row = await session.get(PrehistoryRow, mirror)
        assert mirror_row is not None and mirror_row.source_world_id == mirrored.mirror_twin_id and mirror_row.kind is PrehistoryKind.MIRRORED
        events = list(await session.scalars(select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == mirror)))
        assert all(event.mirrored and event.source is PrehistorySource.MIRRORED for event in events)
        ship_row = await session.get(PrehistoryRow, ship)
        assert ship_row is not None and ship_row.source_world_id is not None
        origin = await session.get(WorldRow, ship_row.source_world_id)
        assert origin is not None and origin.discovery is Discovery.FORGOTTEN
        departure = await session.scalar(select(PrehistoryEventRow).where(PrehistoryEventRow.world_id == ship, PrehistoryEventRow.subject_node_id == origin.id))
        assert departure is not None


async def test_realms_of_the_dead_palaces_and_dream_worlds_borrow_dream_and_tell_their_pasts(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        son = cosmos.sons[0]
    dead = await world_of_kind(database, "Ashen Halls", WorldType.DEAD)
    palace = await world_of_kind(database, "High Seat", WorldType.GODS_PALACE, son_id=son.id)
    dream = await world_of_kind(database, "Night Field", WorldType.DREAM)
    async with database.write() as session:
        ctx = await manual_context(session, "test_prehistory", Rules())
        home = cosmos.home.world.id
        await ctx.chronicle(ChronicleKind.DEATH, "The old queen died.", template_key="test.death", world_id=home, magnitude=60)
        await ctx.chronicle(ChronicleKind.DREAM, "A herder dreamt of a field at night.", template_key="test.dream", world_id=home, magnitude=50)
        await ctx.chronicle(ChronicleKind.WORLD, "The god raised a hall.", template_key="test.deed", son_id=son.id, magnitude=70)
        for world_id in (dead, palace, dream):
            await configure(ctx, world_id, 1, 1)
    for world_id in (dead, palace, dream):
        await run_prehistory(database, world_id)
    async with database.write() as session:
        for world_id, kind in ((dead, PrehistoryKind.SOULS), (palace, PrehistoryKind.PALACE), (dream, PrehistoryKind.DREAMT)):
            row = await session.get(PrehistoryRow, world_id)
            assert row is not None and row.kind is kind and row.state is PrehistoryState.DONE and row.rounds_done == 0
            assert await session.scalar(select(func.count()).select_from(PrehistoryEventRow).where(PrehistoryEventRow.world_id == world_id))
        ctx = await manual_context(session, "test_prehistory", Rules())
        world = await session.get(WorldRow, dream)
        row = await session.get(PrehistoryRow, dream)
        assert world is not None and row is not None
        await ctx.chronicle(ChronicleKind.DREAM, "A fisher dreamt of the same field.", template_key="test.dream", world_id=home, magnitude=90)
        assert await dreams_of(ctx, row, world) >= 2


async def test_deep_time_runs_the_cosmos_forward_and_keeps_its_strongest_happenings(database: Database) -> None:
    async with database.write() as session:
        await seed_rich_cosmos(session)
        start = (await CosmosRepository(session).require_cosmos()).epoch
        run = await open_run(await manual_context(session, "test_deep_time", Rules()), 1)
        run_id = run.id
    summary = await fast_forward(database, run_id)
    assert summary.epochs == 1 and summary.state is DeepTimeState.DONE
    async with database.read() as session:
        stored = await session.get(DeepTimeRunRow, run_id)
        assert stored is not None and stored.ran == 1 and stored.to_epoch >= start and stored.sons_simulated >= 1
        kept = int(await session.scalar(select(func.count()).select_from(DeepTimeEventRow).where(DeepTimeEventRow.run_id == run_id)) or 0)
        assert kept <= Rules().prehistory.deep_time_digest_size


async def test_a_world_with_lore_is_backfilled_from_it_and_a_planned_past_runs_at_the_end_of_the_age(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        world = cosmos.home.world
        ctx = await manual_context(session, "test_prehistory", Rules())
        fallen = await entity(session, "Old Crown", EntityType.POLITY, PolityStats(), world_id=world.id)
        fallen.status, fallen.end_epoch, fallen.importance = EntityStatus.DEAD, 1, 80
        await session.flush()
        assert await backfill_world(ctx, world) >= 1
        row = await session.get(PrehistoryRow, world.id)
        assert row is not None and row.source is PrehistorySource.BACKFILLED and row.state is PrehistoryState.DONE
        planned = await prehistory_of(ctx, cosmos.frontiers[2].world, 1, 1)
        planned_id = planned.world_id
    assert await born_prehistories(database, 10_000) == 1
    async with database.read() as session:
        done = await session.get(PrehistoryRow, planned_id)
        assert done is not None and done.state is PrehistoryState.DONE


TOLD_WITH = frozenset({"incident_participants", "chronicle_entities"})


class OutsideWatcher:
    def __init__(self, world_id: int, inside: set[int]) -> None:
        self.world_id = world_id
        self.inside = inside
        self.leaks: Counter[str] = Counter()
        self.origins: dict[int, str] = {}

    def pending(self, _session: Session, row: object) -> None:
        self.origins[id(row)] = origin()

    def after_flush(self, session: Session, _context: object) -> None:
        for row in session.new:
            where = self.origins.get(id(row), "?")
            if isinstance(row, EntityRow | ForeignGodRow) and row.world_id is not None and row.world_id != self.world_id:
                self.leaks[f"{table_of(row)} born on another world at {where}"] += 1
            elif isinstance(row, ChronicleRow) and row.world_id is not None and row.world_id != self.world_id:
                self.leaks[f"chronicle of another world at {where}"] += 1
            elif not isinstance(row, EntityRow | ForeignGodRow | ChronicleRow) and table_of(row) not in TOLD_WITH and tied_to_a_node(row):
                shape = owned_shape(object_mapper(row))
                owners = owner_ids(row, shape) if shape is not None else []
                if owners and all(owner not in self.inside for owner in owners):
                    self.leaks[f"{table_of(row)} tied only to held nodes at {where}"] += 1


async def test_a_prehistory_on_a_stirred_cosmos_with_every_chance_certain_leaves_every_other_world_untouched(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        await stir(session, cosmos)
        target = cosmos.home.world.id
        ctx = await manual_context(session, "test_prehistory", Rules())
        await configure(ctx, target, 2, 1)
    watchers: list[OutsideWatcher] = []
    original = prerun.follow_inside

    def watched(world_id: int, inside: set[int]) -> Callable[..., None]:
        watcher = OutsideWatcher(world_id, inside)
        watchers.append(watcher)
        event.listen(Session, "transient_to_pending", watcher.pending)
        event.listen(Session, "after_flush", watcher.after_flush)
        return original(world_id, inside)

    prerun.follow_inside = watched
    try:
        await run_prehistory(database, target, rules=eager(Rules()))
    finally:
        prerun.follow_inside = original
        for watcher in watchers:
            event.remove(Session, "transient_to_pending", watcher.pending)
            event.remove(Session, "after_flush", watcher.after_flush)
    leaks = Counter[str]()
    for watcher in watchers:
        leaks.update(watcher.leaks)
    assert not leaks, "Steps that reach past the held worlds during a prehistory:\n" + "\n".join(f"{count}x {leak}" for leak, count in leaks.most_common())
