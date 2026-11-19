import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.epochs import EpochStatsRow
from aerona.db.telemetry.setup import setup_telemetry
from aerona.db.telemetry.tables import LiveEventRow, LlmCallRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus
from aerona.domain.models.entity_stats import FactionStats, SettlementStats
from aerona.domain.models.records import EpochStatsData, SonEpochStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services import search, son_relations, state, statistics, wiki
from aerona.services.metrics import ErrorRing, HealthStatus, MetricsService, health, step_group
from tests.engine.core.factories import region_record
from tests.services.app.factories import Cosmos, bond, make_entity, make_son, make_world


async def test_search_index_names_and_path(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    await ChronicleRepository(session).append(ChronicleDraft(epoch=1, kind=ChronicleKind.WORLD, text="The Velari Folk sang of salt."))
    index = search.SearchIndex()
    hits = await search.search(session, rules, index, "velari", "v1")
    assert [hit.category for hit in hits][:2] == [search.SearchCategory.ENTITY, search.SearchCategory.CHRONICLE]
    assert hits[0].title == "Velari Folk"
    assert hits[1].snippet == "The Velari Folk sang of salt."
    assert await search.search(session, rules, index, "v", "v1") == []
    found = await search.search_entities(session, rules, "amber")
    assert [entity.name for entity in found] == ["Amberreach"]
    names = await search.names_index(session)
    assert {entry.kind for entry in names} == {NodeKind.ENTITY, NodeKind.SON, NodeKind.WORLD, NodeKind.STAR, NodeKind.CREATOR}
    other = await make_world(session, "Dusk")
    path = await search.find_path(session, world.people.id, other.id)
    assert not path.found
    path = await search.find_path(session, world.people.id, world.son.id)
    assert path.found
    assert path.path[0] == world.people.id and path.path[-1] == world.son.id
    assert search.snippet("x" * 50 + "needle" + "y" * 200, "needle").startswith("…")


async def test_graph_assembly(session: AsyncSession, world: Cosmos) -> None:
    await bond(session, world.people.id, world.son.id, BondKind.WORSHIPS)
    built = await search.graph(session)
    kinds = {node.kind for node in built.nodes}
    assert kinds == {NodeKind.SON, NodeKind.ENTITY, NodeKind.CREATOR}
    assert any(link.kind is BondKind.WORSHIPS for link in built.links)


async def test_graph_shows_active_and_past_bonds_but_never_hidden_ones(session: AsyncSession, world: Cosmos) -> None:
    kinds = {
        BondState.ACTIVE: BondKind.WORSHIPS,
        BondState.PAST: BondKind.ALLY,
        BondState.HIDDEN_REJECTED: BondKind.ENEMY,
        BondState.HIDDEN_CLOSED: BondKind.RIVAL,
    }
    for kind in kinds.values():
        await bond(session, world.people.id, world.son.id, kind)
    for row in await session.scalars(select(BondRow).where(BondRow.kind.in_(list(kinds.values())))):
        row.state = next(state for state, kind in kinds.items() if kind is row.kind)
    await session.flush()
    links = {(link.kind, link.past) for link in (await search.graph(session)).links}
    assert (BondKind.WORSHIPS, False) in links and (BondKind.ALLY, True) in links
    assert not {kind for kind, _ in links} & {BondKind.ENEMY, BondKind.RIVAL}


async def test_wiki_politics_roads_tiers(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    region_b = await make_entity(session, "Greenvale", EntityType.REGION, world_id=world.world.id)
    session.add(
        WorldMapRow(
            world_id=world.world.id,
            generator_version=1,
            epoch=1,
            geometry={
                "regions": [
                    region_record(world.region.id, [region_b.id]).model_dump(mode="json"),
                    region_record(region_b.id, [world.region.id]).model_dump(mode="json"),
                ]
            },
        )
    )
    town = await make_entity(
        session, "Brinetown", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats(population=12000)
    )
    port = await make_entity(
        session, "Greenport", EntityType.SETTLEMENT, world_id=world.world.id, location_id=region_b.id, stats=SettlementStats(population=300)
    )
    guild = await make_entity(
        session, "Salt Guild", EntityType.FACTION, world_id=world.world.id, location_id=world.region.id, stats=FactionStats(strength=10, sway=10)
    )
    await bond(session, world.people.id, town.id, BondKind.RULES)
    await bond(session, world.people.id, port.id, BondKind.RULES)
    await bond(session, town.id, port.id, BondKind.TRADES_WITH)
    town.map_x, town.map_y, port.map_x, port.map_y = 0.0, 0.0, 3.0, 4.0
    await session.flush()
    politics = await wiki.political_map(session, rules, world.world.id)
    assert politics[world.region.id].ruler_id == world.people.id
    assert politics[world.region.id].contested
    assert guild.id != politics[world.region.id].ruler_id
    roads = await wiki.road_network(session, world.world.id)
    assert roads == [wiki.Road(town.id, port.id, wiki.RoadKind.TRADE, 5.0)]
    tiers = await wiki.settlement_tiers(session, rules, world.world.id, 2)
    assert tiers[town.id].tier is wiki.SettlementTier.CAPITAL
    assert tiers[port.id].tier is wiki.SettlementTier.VILLAGE
    assert await wiki.take_snapshot(session, rules, 1) == 1
    view = await wiki.historical_view(session, world.world.id, 1)
    assert view is not None
    assert town.id in {entity.id for entity in view.entities}
    assert view.population[town.id] == 12000
    tiers = await wiki.settlement_tiers(session, rules, world.world.id, 2)
    assert tiers[town.id].previous_population == 12000
    note = await wiki.add_map_note(session, x=1.4, y=2.6, text=" Salt here ", color=None, world_id=None)
    assert (note.x, note.y, note.text, note.color) == (1, 3, "Salt here", "gold")
    await wiki.delete_map_note(session, note.id)
    similar = await wiki.similar_entities(session, town.id, 5)
    assert port.id in {item.entity.id for item in similar}
    await wiki.set_favorite(session, town.id, True)
    assert [entity.id for entity in await wiki.favorites(session)] == [town.id]
    await bond(session, world.people.id, world.son.id, BondKind.WORSHIPS)
    dominance = await wiki.region_dominance(session, world.world.id)
    assert dominance[world.region.id].son_id == world.son.id


async def test_state_and_statistics(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    rival = await make_son(session, "Vessa", world.world.id)
    await son_relations.set_relation(session, rules, world.son.id, rival.id, value=50)
    snapshot = await state.snapshot(session, rules)
    assert snapshot.cosmos is not None
    assert snapshot.counts[EntityType.PEOPLE] == 1
    first = snapshot.sons[0]
    assert first.max_hp > 0
    assert first.card.best_friend is not None and first.card.best_friend[0] == rival.id
    assert snapshot.pending_son_ids == [world.son.id, rival.id]
    session.add(EpochStatsRow(epoch=1, data=EpochStatsData(population=100, sons={world.son.id: SonEpochStats(faith=1)})))
    await session.flush()
    world.cosmos.epoch = 2
    rows = await statistics.series(session)
    assert [(row.epoch, row.live) for row in rows] == [(1, False), (2, True)]
    detail = await statistics.breakdown(session, 2)
    assert detail.previous is not None
    assert detail.deltas["population"] == (detail.current.population if detail.current else 0) - 100


async def test_metrics_summary_eta_and_health(tmp_path: Path) -> None:
    telemetry = await setup_telemetry(f"sqlite+aiosqlite:///{tmp_path / 'telemetry.db'}")
    rules = Rules()
    service = MetricsService(telemetry, lambda: rules)
    async with telemetry.sessions() as session, session.begin():
        for epoch, duration, status in ((1, 1000, LlmCallStatus.OK), (2, 200_000, LlmCallStatus.ERROR), (200, 10, LlmCallStatus.OK)):
            session.add(
                LlmCallRow(
                    epoch=epoch,
                    job="Son turn: Ithren",
                    model="haiku",
                    kind=LlmCallKind.AGENT,
                    status=status,
                    duration_ms=duration,
                    attempts=2,
                    error="boom" if status is LlmCallStatus.ERROR else None,
                )
            )
        for seconds, phase in ((0, 1), (10, 2), (50, 5)):
            session.add(LiveEventRow(timestamp_ms=1, kind=EventKind.EPOCH_PROGRESS.value, data={"phase": phase, "seconds": seconds}))
        session.add(LiveEventRow(timestamp_ms=2, kind=EventKind.EPOCH_FINISHED.value, data={"seconds": 60}))
    summary = await service.summary(10)
    assert summary.totals.calls == 3
    assert summary.steps[0].step == "Son turns"
    assert len(summary.slowest) == 1
    assert len(summary.latest_errors) == 1
    assert step_group("Mortal turn: Ora") == "Mortal turns"
    estimate = await service.estimate(started_at=datetime.now(UTC), phase=None, phase_started_at=None)
    assert estimate.samples == 1
    assert estimate.average_epoch_seconds == 60
    assert estimate.remaining_seconds is not None
    assert await service.prune() == 2
    ring = ErrorRing()
    logger = logging.getLogger("aerona.test")
    logger.addHandler(ring)
    logger.error("database exploded")
    report = health(
        rules=rules,
        ring=ring,
        database_path=tmp_path / "telemetry.db",
        log_file=tmp_path / "log",
        latest_backup=None,
        backup_count=0,
        running_jobs=0,
        read_only=False,
        uptime_seconds=1,
    )
    assert report.status == HealthStatus.WARNING
    assert report.recent_errors[0].text == "database exploded"
    logger.removeHandler(ring)
    await telemetry.dispose()


def test_settlement_tiers_reach_megacities_and_conurbations() -> None:
    rules = Rules()
    politics = rules.politics
    assert wiki.settlement_tier(rules, politics.metropolis_population) is wiki.SettlementTier.GREAT_CITY
    assert wiki.settlement_tier(rules, politics.megacity_population) is wiki.SettlementTier.MEGACITY
    assert wiki.settlement_tier(rules, politics.conurbation_population) is wiki.SettlementTier.CONURBATION
    assert wiki.settlement_tier(rules, politics.megacity_population - 1) is wiki.SettlementTier.GREAT_CITY
