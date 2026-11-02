from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from aerona.constants.migration import REPORT_JSON_NAME, REPORT_MARKDOWN_NAME


class ReportItem(BaseModel):
    category: str
    reference: str
    detail: str


class Rename(BaseModel):
    kind: str
    legacy_id: int | None
    original: str
    migrated: str


class RuleMapping(BaseModel):
    legacy_key: str
    target: str | None
    value: float | None
    status: str


class ImageSummary(BaseModel):
    rows: int = 0
    linked: int = 0
    uploaded: int = 0
    deduplicated: int = 0
    already_stored: int = 0
    bytes_uploaded: int = 0
    missing_files: int = 0
    unlinked: int = 0
    skipped_thumbnails: int = 0
    files_without_rows: int = 0


class MigrationReport(BaseModel):
    legacy_path: str
    target_path: str
    dry_run: bool
    media_backend: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    succeeded: bool = False
    error: str | None = None
    legacy_epoch: int | None = None
    legacy_missing_columns: dict[str, list[str]] = Field(default_factory=dict)
    legacy_unknown_columns: dict[str, list[str]] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(default_factory=dict)
    target_counts: dict[str, int] = Field(default_factory=dict)
    conversions: dict[str, int] = Field(default_factory=dict)
    renames: list[Rename] = Field(default_factory=list)
    unplaced: list[ReportItem] = Field(default_factory=list)
    warnings: list[ReportItem] = Field(default_factory=list)
    unknown_tags: dict[str, int] = Field(default_factory=dict)
    kept_system_tags: dict[str, int] = Field(default_factory=dict)
    free_tags: dict[str, int] = Field(default_factory=dict)
    dropped_stats: dict[str, int] = Field(default_factory=dict)
    rules: list[RuleMapping] = Field(default_factory=list)
    images: ImageSummary = Field(default_factory=ImageSummary)
    repairs: dict[str, int] = Field(default_factory=dict)
    checks: dict[str, str] = Field(default_factory=dict)
    not_migrated: dict[str, int] = Field(default_factory=dict)

    def convert(self, key: str, amount: int = 1) -> None:
        self.conversions[key] = self.conversions.get(key, 0) + amount

    def place_failed(self, category: str, reference: str, detail: str) -> None:
        self.unplaced.append(ReportItem(category=category, reference=reference, detail=detail))

    def warn(self, category: str, reference: str, detail: str) -> None:
        self.warnings.append(ReportItem(category=category, reference=reference, detail=detail))

    def renamed(self, kind: str, legacy_id: int | None, original: str, migrated: str) -> None:
        self.renames.append(Rename(kind=kind, legacy_id=legacy_id, original=original, migrated=migrated))

    def tag_unknown(self, tag: str) -> None:
        self.unknown_tags[tag] = self.unknown_tags.get(tag, 0) + 1

    def tag_kept(self, tag: str) -> None:
        self.kept_system_tags[tag] = self.kept_system_tags.get(tag, 0) + 1

    def tag_free(self, tag: str) -> None:
        self.free_tags[tag] = self.free_tags.get(tag, 0) + 1

    def stat_dropped(self, key: str) -> None:
        self.dropped_stats[key] = self.dropped_stats.get(key, 0) + 1

    def finish(self, error: str | None = None) -> None:
        self.finished_at = datetime.now(UTC)
        self.error = error
        self.succeeded = error is None

    def category_counts(self, items: list[ReportItem]) -> Counter[str]:
        return Counter(item.category for item in items)


def write_report(report: MigrationReport, directory: Path, markdown: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / REPORT_JSON_NAME
    markdown_path = directory / REPORT_MARKDOWN_NAME
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path
