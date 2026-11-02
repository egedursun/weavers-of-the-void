from sqlalchemy import func, select, text

from aerona.db.base import Base
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NameRegistryRow, NodeRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.world import LoreLanguage
from aerona.engine.cosmos.maps import store_world_map
from aerona.engine.primitives.canon_facts import seed_if_empty
from aerona.events.bus import EventBus
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.errors import MigrationError
from aerona.services.bonds import BondService
from aerona.services.chronicle import ChronicleWriter
from aerona.services.images.records import clear_file_name_captions
from aerona.services.importance import persist_if_missing
from aerona.services.integrity.age_consistency import raise_lifespans
from aerona.services.integrity.data_repairs import DataRepairs
from aerona.services.integrity.graph_ends import repair_graph_ends
from aerona.services.integrity.network import RepairLog
from aerona.services.narrative import backfill_endings, sweep_narratives
from aerona.services.notifications import Notifier

INTEGRITY_OK = "ok"
PASSED = "passed"
SKIPPED_FOR_LORE_LANGUAGE = "skipped_english_text_repairs"


async def run_repairs(context: MigrationContext) -> None:
    session, rules, epoch = context.session, context.rules, context.epoch
    log = RepairLog()
    repairs = DataRepairs(BondService(ChronicleWriter(Notifier(EventBus()))), log)
    counters = {"importance": await persist_if_missing(session, rules, epoch), "mortal_ages": await raise_lifespans(session, rules)}
    counters.update(await repairs.run(session, rules))
    counters["graph_ends"] = (await repair_graph_ends(session, rules, epoch, log)).total
    counters["captions"] = await clear_file_name_captions(session)
    counters["certain_facts"] = await seed_if_empty(session)
    cosmos = await CosmosRepository(session).require_cosmos()
    if cosmos.lore_language is LoreLanguage.ENGLISH:
        counters["narrative_leaks"] = await sweep_narratives(session)
        counters["endings"] = await backfill_endings(session)
    else:
        counters[SKIPPED_FOR_LORE_LANGUAGE] = 1
    await session.flush()
    context.report.repairs.update(counters)


async def regenerate_maps(context: MigrationContext) -> None:
    for world in list(await context.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        world_map = await store_world_map(context.session, context.rules, world, context.epoch)
        context.report.convert("maps_generated")
        context.report.convert("map_regions", len(world_map.regions))
        context.report.convert("map_markers", len(world_map.markers))
        context.report.convert("map_positions_new", len(world_map.new_positions))
        context.report.convert("map_positions_relocated", len(world_map.relocated_positions))


async def check_constraints(context: MigrationContext) -> None:
    session = context.session
    await session.flush()
    violations = list(await session.execute(text("PRAGMA foreign_key_check")))
    if violations:
        tables = sorted({str(row[0]) for row in violations})
        raise MigrationError(f"Foreign key check failed in {len(violations)} rows ({', '.join(tables)}).")
    context.report.checks["foreign_keys"] = PASSED
    integrity = await session.scalar(text("PRAGMA integrity_check"))
    if str(integrity) != INTEGRITY_OK:
        raise MigrationError(f"Integrity check failed: {integrity}.")
    context.report.checks["integrity"] = PASSED
    named = await session.scalar(select(func.count(NodeRow.id)).where(NodeRow.id.not_in(select(EntityRow.id).where(EntityRow.status == EntityStatus.REJECTED))))
    registered = await session.scalar(select(func.count()).select_from(NameRegistryRow))
    if named != registered:
        raise MigrationError(f"Name registry mismatch: {named} named records, {registered} registered names.")
    context.report.checks["name_registry"] = PASSED


async def count_tables(context: MigrationContext) -> None:
    for table in Base.metadata.sorted_tables:
        amount = await context.session.scalar(select(func.count()).select_from(table))
        if amount:
            context.report.target_counts[table.name] = int(amount)
