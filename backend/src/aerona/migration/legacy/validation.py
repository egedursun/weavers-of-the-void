from aerona.migration.legacy.errors import LegacyValidationError
from aerona.migration.legacy.report import MigrationReport
from aerona.migration.legacy.source import LegacyRow, LegacySource

CORE_TABLES = ("world_state", "sons", "entities", "bonds", "chronicle", "stars", "worlds")
TURN_TABLES = ("sons", "entities")
PENDING_JOB = "pending job"


def check_schema(source: LegacySource, report: MigrationReport) -> None:
    present = source.physical_tables()
    missing_tables = [name for name in CORE_TABLES if source.table_spec(name).name not in present]
    if missing_tables:
        raise LegacyValidationError(f"The legacy database is missing core tables: {', '.join(missing_tables)}.")
    for name in source.vocabulary.tables:
        if not source.has(name):
            report.legacy_missing_columns[name] = ["(table)"]
            continue
        missing = source.missing_columns(name)
        unknown = source.unknown_columns(name)
        if missing:
            report.legacy_missing_columns[name] = missing
        if unknown:
            report.legacy_unknown_columns[name] = unknown
        absent_required = [column for column in source.table_spec(name).required if column in missing]
        if absent_required:
            raise LegacyValidationError(f"Unknown legacy schema: {name} lacks {', '.join(absent_required)}.")


def check_world(source: LegacySource) -> tuple[LegacyRow, int]:
    state = source.single("world_state")
    if state is None:
        raise LegacyValidationError("The legacy world has not been created.")
    epoch = state.integer("epoch")
    if epoch is None or epoch < 1:
        raise LegacyValidationError("The legacy world has no valid epoch.")
    if state.text("epoch_state") is not None:
        raise LegacyValidationError("The legacy epoch is still in progress; finish it before migrating.")
    if source.count("worlds") == 0:
        raise LegacyValidationError("The legacy world predates the multi-world cosmos; open it once in the legacy app first.")
    return state, epoch


def check_turns(source: LegacySource, report: MigrationReport, epoch: int) -> None:
    pending_key = source.vocabulary.texts.pending_job_key
    for table in TURN_TABLES:
        for row in source.iterate(table):
            if row.integer("turn_epoch") == epoch and row.raw("turn_points") is not None:
                raise LegacyValidationError(f"A legacy {table} turn is paused in epoch {epoch}; finish the epoch before migrating.")
            context = row.text("turn_context")
            if context is not None and pending_key in context:
                report.warn(PENDING_JOB, f"{table}:{row.integer('id')}", "a pending job inside a finished turn was dropped")


def validate(source: LegacySource, report: MigrationReport) -> int:
    check_schema(source, report)
    _, epoch = check_world(source)
    check_turns(source, report, epoch)
    report.legacy_epoch = epoch
    return epoch
