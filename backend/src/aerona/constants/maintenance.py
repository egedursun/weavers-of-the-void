BACKUP_PREFIX = "aerona"
BACKUP_SUFFIX = ".db"
BACKUP_MANIFEST_SUFFIX = ".json"
SECONDARY_TARGET_FILENAME = "secondary-backup-target.json"
SECONDARY_TARGET_KEY = "directory"
BACKUP_LABEL_MAX_LENGTH = 40
BACKUP_RANDOM_LENGTH = 4
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"
MANUAL_LABEL = "manual"
EPOCH_LABEL_PREFIX = "epoch"
RESTORE_SAFETY_LABEL = "before-restore"
IMPORT_SAFETY_LABEL = "before-import"
RESET_SAFETY_LABEL = "before-reset"
CORE_TABLES = ("cosmos", "sons", "entities", "chronicle")
SAFE_FILE_NAME_PATTERN = r"^[\w-][\w.-]*$"
SAFE_IMAGE_NAME_MAX_LENGTH = 200
RASTER_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"})
PACKAGE_FORMAT = "aerona-world"
PACKAGE_VERSION = 2
PACKAGE_SUFFIX = ".aerona"
PACKAGE_NAME_MAX_LENGTH = 40
PACKAGE_MANIFEST_MEMBER = "manifest.json"
PACKAGE_DATABASE_MEMBER = "world.db"
PACKAGE_MEDIA_MEMBER_PREFIX = "media/"
PACKAGE_MANIFEST_MAX_BYTES = 8 * 1024 * 1024
PACKAGE_OBJECT_MAX_BYTES = 30 * 1024 * 1024
PACKAGE_COPY_BUFFER_BYTES = 1024 * 1024
IMPORTED_OBJECT_PREFIX = "imported-"
IMPORTED_OBJECT_TOKEN_BYTES = 4
PACKAGE_MAX_BYTES = 400 * 1024 * 1024
PACKAGE_MAX_DECOMPRESSED_BYTES = 500 * 1024 * 1024
PACKAGE_READ_BYTES = 1024 * 1024
WORK_DIRNAME = "work"
DISCOVERY_DIRNAME = "discovery"
DISCOVERY_STATE_FILENAME = "discovery.json"
REPLACE_CONFIRMATION = "REPLACE"
RESTORE_CONFIRMATION = "RESTORE"
RESET_CONFIRMATION = "RESET"
MERGE_CONFIRMATION = "MERGE"
MERGE_SKIPPED_TABLES = frozenset(
    {
        "achievements",
        "action_records",
        "agent_turns",
        "applied_fixups",
        "cosmos",
        "councils",
        "creator",
        "creator_mood_inputs",
        "deferred_steps",
        "epoch_agents",
        "epoch_engine_phases",
        "epoch_phase_timings",
        "epoch_runs",
        "epoch_stats",
        "epoch_steps",
        "epoch_year_cursors",
        "epochs",
        "god_conflicts",
        "jobs",
        "ledger_changes",
        "ledger_entries",
        "map_snapshots",
        "messages",
        "name_registry",
        "notifications",
        "rule_overrides",
        "scenarios",
        "scores",
        "turn_counters",
    }
)
MERGE_SKIPPED_NODE_KINDS = frozenset({"son", "creator"})
MERGE_IMAGE_PREFIX = "merged"
MERGE_PRAGMA_DEFER = "PRAGMA defer_foreign_keys = ON"
MERGE_FOREIGN_KEY_CHECK = "PRAGMA foreign_key_check"
