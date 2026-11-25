from dataclasses import dataclass
from pathlib import Path

from aerona.constants.maintenance import DISCOVERY_DIRNAME, DISCOVERY_STATE_FILENAME, SECONDARY_TARGET_FILENAME, WORK_DIRNAME
from aerona.constants.paths import (
    ADOPTION_MARKER_FILENAME,
    BACKUPS_DIRNAME,
    DATABASE_FILENAME,
    EXPORTS_DIRNAME,
    FORECASTS_DIRNAME,
    IMPORTS_DIRNAME,
    LIBRARY_DATABASE_FILENAME,
    LOG_FILENAME,
    LOGS_DIRNAME,
    MEDIA_DIRNAME,
    MODELS_DIRNAME,
    OUTGOING_DIRNAME,
    SQLITE_COMPANION_SUFFIXES,
    TRASH_DIRNAME,
    UNIVERSE_MANIFEST_FILENAME,
    UNIVERSES_DIRNAME,
)
from aerona.constants.telemetry import TELEMETRY_DATABASE_FILENAME


def with_companions(database: Path) -> tuple[Path, ...]:
    return (*(database.with_name(database.name + suffix) for suffix in SQLITE_COMPANION_SUFFIXES), database)


@dataclass(frozen=True)
class UniversePaths:
    root: Path

    @property
    def database(self) -> Path:
        return self.root / DATABASE_FILENAME

    @property
    def media(self) -> Path:
        return self.root / MEDIA_DIRNAME

    @property
    def backups(self) -> Path:
        return self.root / BACKUPS_DIRNAME

    @property
    def exports(self) -> Path:
        return self.root / EXPORTS_DIRNAME

    @property
    def work(self) -> Path:
        return self.root / WORK_DIRNAME

    @property
    def forecasts(self) -> Path:
        return self.root / FORECASTS_DIRNAME

    @property
    def discovery(self) -> Path:
        return self.root / DISCOVERY_DIRNAME

    @property
    def discovery_state(self) -> Path:
        return self.root / DISCOVERY_STATE_FILENAME

    @property
    def secondary_target(self) -> Path:
        return self.root / SECONDARY_TARGET_FILENAME

    @property
    def telemetry(self) -> Path:
        return self.root / TELEMETRY_DATABASE_FILENAME

    @property
    def manifest(self) -> Path:
        return self.root / UNIVERSE_MANIFEST_FILENAME

    def owned(self) -> tuple[Path, ...]:
        return (
            self.media,
            self.backups,
            self.exports,
            self.work,
            self.forecasts,
            self.discovery,
            self.discovery_state,
            self.secondary_target,
            *with_companions(self.telemetry),
            *with_companions(self.database),
        )


@dataclass(frozen=True)
class ProcessPaths:
    root: Path

    @property
    def library_database(self) -> Path:
        return self.root / LIBRARY_DATABASE_FILENAME

    @property
    def logs(self) -> Path:
        return self.root / LOGS_DIRNAME

    @property
    def log_file(self) -> Path:
        return self.logs / LOG_FILENAME

    @property
    def models(self) -> Path:
        return self.root / MODELS_DIRNAME

    @property
    def universes(self) -> Path:
        return self.root / UNIVERSES_DIRNAME

    @property
    def imports(self) -> Path:
        return self.root / IMPORTS_DIRNAME

    @property
    def trash(self) -> Path:
        return self.root / TRASH_DIRNAME

    @property
    def outgoing(self) -> Path:
        return self.root / OUTGOING_DIRNAME

    @property
    def adoption_marker(self) -> Path:
        return self.root / ADOPTION_MARKER_FILENAME

    @property
    def legacy(self) -> UniversePaths:
        return UniversePaths(self.root)

    def universe(self, universe_id: str) -> UniversePaths:
        return UniversePaths(self.universes / universe_id)
