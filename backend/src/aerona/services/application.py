import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, UOWTransaction
from sqlalchemy.orm.attributes import instance_state

from aerona.agents.metrics import TelemetrySink
from aerona.agents.ports import LanguageModel, bus_publisher
from aerona.agents.runtime import AgentRuntime
from aerona.agents.tool_ports import attach_toolkits
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.telemetry.setup import TelemetryDatabase, setup_telemetry, telemetry_url
from aerona.domain.enums.job import JobKind
from aerona.events.bus import EventBus
from aerona.events.change_feed import TRACKED_TABLE_NAMES, ChangeFeed, ChangeOperation
from aerona.events.kinds import EventKind
from aerona.imaging.client import ImageWorkerClient
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.llm.client import LlmClient
from aerona.media.factory import create_media_store
from aerona.media.store import MediaStore
from aerona.rules.registry import Rules
from aerona.services.agent_ports import agent_lore_ports
from aerona.services.backups import BackupService
from aerona.services.bonds import BondService
from aerona.services.bulk_deepen import BulkDeepening
from aerona.services.chronicle import ChronicleWriter
from aerona.services.discovery import DiscoveryService
from aerona.services.exchange import ExchangeService, WorldChangedHook
from aerona.services.images.media import Thumbnailer
from aerona.services.images.queue import ImageQueue
from aerona.services.images.records import ImageRecords
from aerona.services.importance import persist
from aerona.services.integrity.containment import close_market_trade, close_mismatched_inside
from aerona.services.integrity.data_repairs import GRAPH_ENDS_STEP, DataRepairs, checkpoint, history_signed, refresh_planner_statistics, sign_history
from aerona.services.integrity.graph_ends import repair_at_epoch_end
from aerona.services.integrity.network import RepairLog
from aerona.services.ledger import Ledger
from aerona.services.live_log import LiveLog
from aerona.services.lore_ports import LorePorts
from aerona.services.metrics import ErrorRing, MetricsService, capture_loop_errors, install_error_ring
from aerona.services.motifs import MotifCache
from aerona.services.notification_stream import NotificationStream
from aerona.services.notifications import Notifier, prune_notifications
from aerona.services.rules import RulesService
from aerona.services.search import SearchIndex
from aerona.services.startup_completion import StartupCompletion
from aerona.services.wiki import take_snapshot
from aerona.services.world_merge import WorldMerger
from aerona.settings import Settings

logger = logging.getLogger(__name__)

PENDING_CHANGES = "aerona.pending_changes"
COMPLETION_GROUP = "completion"
MILLISECONDS = 1000
VOLATILE_TABLES = frozenset({"cosmos", "creator"})
VOLATILE_COSMOS_COLUMNS = frozenset({"epoch", "epoch_start_year", "map_version", "doom_clock", "updated_at", "rules_snapshot_at", "essence"})


def ready_event() -> asyncio.Event:
    event = asyncio.Event()
    event.set()
    return event


@dataclass
class ApplicationServices:
    feed: ChangeFeed
    notifier: Notifier
    chronicle: ChronicleWriter
    ledger: Ledger
    bonds: BondService
    backups: BackupService
    discovery: DiscoveryService
    world_changed: WorldChangedHook
    exchange: ExchangeService
    telemetry: TelemetryDatabase
    metrics: MetricsService
    errors: ErrorRing
    live_log: LiveLog
    notification_stream: NotificationStream
    search: SearchIndex
    motifs: MotifCache
    repair_log: RepairLog
    repairs: DataRepairs
    media: MediaStore
    image_records: ImageRecords
    thumbnails: Thumbnailer
    images: ImageQueue
    bulk_deepen: BulkDeepening
    completion: StartupCompletion
    ports: LorePorts
    image_client: ImageWorkerClient
    model: LanguageModel
    agents: AgentRuntime
    background: set[asyncio.Task[Any]] = field(default_factory=set)
    repairs_ready: asyncio.Event = field(default_factory=ready_event)


def meaningful_update(instance: object) -> bool:
    if getattr(instance, "__tablename__", None) not in VOLATILE_TABLES:
        return True
    changed = {attribute.key for attribute in instance_state(instance).attrs if attribute.history.has_changes()}
    return bool(changed - VOLATILE_COSMOS_COLUMNS)


def _row_key(instance: object) -> tuple[str, str] | None:
    table = getattr(instance, "__tablename__", None)
    identity = getattr(instance, "id", None)
    if not isinstance(table, str) or table not in TRACKED_TABLE_NAMES or identity is None:
        return None
    return table, str(identity)


def install_change_tracking(database: Database, feed: ChangeFeed) -> None:
    engine: Engine = database.engine.sync_engine
    pending_key = f"{PENDING_CHANGES}.{id(feed)}"

    def after_flush(session: Session, context: UOWTransaction) -> None:
        del context
        if session.get_bind() is not engine:
            return
        pending: list[tuple[str, str, ChangeOperation]] = session.info.setdefault(pending_key, [])
        for operation, instances in ((ChangeOperation.INSERT, session.new), (ChangeOperation.UPDATE, session.dirty), (ChangeOperation.DELETE, session.deleted)):
            for instance in instances:
                key = _row_key(instance)
                if key is not None and (operation is not ChangeOperation.UPDATE or (session.is_modified(instance) and meaningful_update(instance))):
                    pending.append((key[0], key[1], operation))

    def after_commit(session: Session) -> None:
        pending = session.info.pop(pending_key, None)
        if pending:
            feed.record_many(pending)

    def after_rollback(session: Session) -> None:
        session.info.pop(pending_key, None)

    event.listen(Session, "after_flush", after_flush)
    event.listen(Session, "after_commit", after_commit)
    event.listen(Session, "after_rollback", after_rollback)


async def build_application(
    settings: Settings,
    database: Database,
    bus: EventBus,
    rules: RulesService,
    *,
    ports: LorePorts | None = None,
    model: LanguageModel | None = None,
    media_store: MediaStore | None = None,
    jobs: JobManager | None = None,
) -> ApplicationServices:
    def current() -> Rules:
        return rules.current

    feed = ChangeFeed()
    install_change_tracking(database, feed)
    notifier = Notifier(bus)
    chronicle = ChronicleWriter(notifier)
    ledger = Ledger(chronicle, bus)
    bond_service = BondService(chronicle)
    store = media_store or create_media_store(settings)
    await store.ensure_ready()
    discovery = DiscoveryService(settings)
    backups = BackupService(settings, database, current, bus, store=store, pinned=discovery.pinned_objects)
    await discovery.resume()
    world_changed = WorldChangedHook(feed, bus)
    exchange = ExchangeService(settings, backups, discovery, world_changed, WorldMerger(database), store=store)
    telemetry = await setup_telemetry(telemetry_url(settings.data_dir))
    metrics = MetricsService(telemetry, current)
    language_model = model or LlmClient(rules, settings.llm_enabled, metrics.sink(TelemetrySink(telemetry)), publish=bus_publisher(bus))
    agents = attach_toolkits(AgentRuntime(database=database, model=language_model, publish=bus_publisher(bus)))
    errors = ErrorRing()
    install_error_ring(errors)
    live_log = LiveLog(bus, metrics, current)
    await live_log.restore()
    await seed_bus_epoch(database, bus)
    live_log.attach()
    notification_stream = NotificationStream(bus, database, notifier, current, lambda: discovery.active)
    notification_stream.attach()
    search = SearchIndex()
    motifs = MotifCache()
    repair_log = RepairLog()
    lore = ports or agent_lore_ports(agents, current)
    image_records = ImageRecords(backups.collector)
    server = rules.current.server
    thumbnails = Thumbnailer(store, server.thumbnail_concurrency, server.thumbnail_timeout)
    image_client = ImageWorkerClient(settings.image_worker_url)
    images = ImageQueue(database, image_client, image_records, current, bus=bus, prompts=lore.prompts, read_only=lambda: discovery.active, jobs=jobs)
    bulk = BulkDeepening(database, current, lore.deepener, namer=lore.namer, bus=bus, read_only=lambda: discovery.active, jobs=jobs)
    completion = StartupCompletion(database, current, lore, read_only=lambda: discovery.active)
    application = ApplicationServices(
        feed=feed,
        notifier=notifier,
        chronicle=chronicle,
        ledger=ledger,
        bonds=bond_service,
        backups=backups,
        discovery=discovery,
        world_changed=world_changed,
        exchange=exchange,
        telemetry=telemetry,
        metrics=metrics,
        errors=errors,
        live_log=live_log,
        notification_stream=notification_stream,
        search=search,
        motifs=motifs,
        repair_log=repair_log,
        repairs=DataRepairs(bond_service, repair_log),
        media=store,
        image_records=image_records,
        thumbnails=thumbnails,
        images=images,
        bulk_deepen=bulk,
        completion=completion,
        ports=lore,
        image_client=image_client,
        model=language_model,
        agents=agents,
    )
    world_changed.register(rules.load)
    world_changed.register(motifs.clear)
    world_changed.register(search.invalidate)
    world_changed.register(repair_log.clear)
    world_changed.register(lambda: _spawn(application, seed_bus_epoch(database, bus)))
    world_changed.register(lambda: _spawn(application, run_maintenance(application, database, rules)))
    return application


async def seed_bus_epoch(database: Database, bus: EventBus) -> None:
    try:
        async with database.read() as session:
            cosmos = await CosmosRepository(session).get()
        bus.set_epoch(cosmos.epoch if cosmos is not None else None)
    except Exception:
        logger.exception("bus epoch could not be read")


def _spawn(application: ApplicationServices, work: Any) -> None:
    task = asyncio.create_task(work)
    application.background.add(task)
    task.add_done_callback(application.background.discard)


async def run_repair_steps(application: ApplicationServices, database: Database, rules: Rules, *, force_history: bool = False) -> dict[str, int]:
    async with database.read() as session:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            return {}
        epoch = cosmos.epoch
        history = force_history or not await history_signed(session)
    repairs = application.repairs
    steps = [step for step in repairs.startup_steps() if step[0] != GRAPH_ENDS_STEP] + (repairs.history_steps() if history else [])
    counters: dict[str, int] = {}
    for name, step in steps:
        async with database.write() as session:
            counters[name] = await step(session, rules, epoch)
        await asyncio.sleep(0)
    if history:
        async with database.write() as session:
            await sign_history(session)
        counters["history_repairs"] = 1
    return counters


async def run_maintenance(application: ApplicationServices, database: Database, rules: RulesService) -> dict[str, int]:
    if application.discovery.active:
        return {}
    application.repairs_ready.clear()
    try:
        counters = await run_repair_steps(application, database, rules.current)
        await application.metrics.prune()
    except Exception:
        logger.exception("startup maintenance failed")
        return {}
    finally:
        application.repairs_ready.set()
    counters[GRAPH_ENDS_STEP] = await repair_graph_in_background(application, database, rules)
    return counters


async def repair_graph_in_background(application: ApplicationServices, database: Database, rules: RulesService) -> int:
    try:
        async with database.read() as session:
            cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            return 0
        async with database.write() as session:
            return await application.repairs.graph_ends(session, rules.current, cosmos.epoch)
    except Exception:
        logger.exception("background graph repair failed")
        return 0


async def schedule_completion(application: ApplicationServices, jobs: JobManager, rules: RulesService) -> None:
    if not application.completion.enabled() or not (await application.completion.needed()).any:
        return
    await asyncio.sleep(rules.current.server.auto_complete_delay_ms / MILLISECONDS)

    async def handler(context: JobContext) -> dict[str, Any]:
        return await application.completion.run(context)

    if jobs.busy_group(COMPLETION_GROUP) is None:
        await jobs.submit(JobKind.COMPLETION, handler, exclusive_group=COMPLETION_GROUP)


async def start_application(application: ApplicationServices, database: Database, jobs: JobManager, rules: RulesService, llm_enabled: bool) -> None:
    capture_loop_errors(asyncio.get_running_loop())
    _spawn(application, run_maintenance(application, database, rules))
    if llm_enabled:
        _spawn(application, schedule_completion(application, jobs, rules))


async def stop_application(application: ApplicationServices) -> None:
    for task in list(application.background):
        task.cancel()
    await application.notification_stream.drain()
    await application.live_log.drain()
    await application.images.shutdown()
    await application.bulk_deepen.shutdown()
    await application.discovery.shutdown()
    await application.image_client.aclose()
    await application.media.close()
    await application.telemetry.dispose()


def publish_changes(bus: EventBus, feed: ChangeFeed) -> None:
    bus.publish(EventKind.CHANGES_AVAILABLE, {"version": feed.version})


async def epoch_end_maintenance(application: ApplicationServices, database: Database, rules: Rules, epoch: int) -> dict[str, int]:
    async with database.write() as session:
        counters = {
            "importance": await persist(session, rules, epoch),
            "notifications": await prune_notifications(session, rules),
            "ledger": await application.ledger.prune(session, rules, epoch),
        }
        repaired = await repair_at_epoch_end(session, rules, epoch, application.repair_log)
        counters["graph_ends"] = repaired.total if repaired is not None else 0
        counters["containment"] = await close_mismatched_inside(session, epoch) + await close_market_trade(session, epoch)
        counters["snapshots"] = await take_snapshot(session, rules, epoch)
        await refresh_planner_statistics(session)
    counters["metrics"] = await application.metrics.prune()
    counters["change_log"] = application.feed.prune(rules.ui.change_log_max_rows)
    await asyncio.to_thread(checkpoint, database_path(database))
    return counters


def database_path(database: Database) -> Path:
    return Path(str(database.engine.url.database))
