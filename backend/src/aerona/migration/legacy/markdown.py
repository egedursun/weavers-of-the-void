from collections import Counter, defaultdict

from aerona.constants.migration import REPORT_SAMPLE_LIMIT, REPORT_TOP_TAGS
from aerona.migration.legacy.report import MigrationReport, ReportItem

PIPE = "|"
ESCAPED_PIPE = "\\|"


def _cell(value: object) -> str:
    return str(value).replace(PIPE, ESCAPED_PIPE).replace("\n", " ")


def _table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> list[str]:
    if not rows:
        return ["(none)", ""]
    lines = [f"| {' | '.join(headers)} |", f"|{'|'.join('---' for _ in headers)}|"]
    lines.extend(f"| {' | '.join(_cell(value) for value in row)} |" for row in rows)
    lines.append("")
    return lines


def _counts(values: dict[str, int]) -> list[tuple[object, ...]]:
    return [(key, value) for key, value in sorted(values.items())]


def _top(values: dict[str, int], limit: int) -> list[tuple[object, ...]]:
    return [(key, value) for key, value in Counter(values).most_common(limit)]


def _grouped(items: list[ReportItem]) -> list[str]:
    groups: dict[str, list[ReportItem]] = defaultdict(list)
    for item in items:
        groups[item.category].append(item)
    lines: list[str] = []
    for category, entries in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        lines.append(f"### {category} ({len(entries)})")
        lines.append("")
        lines.extend(_table(("Record", "Detail"), [(entry.reference, entry.detail) for entry in entries[:REPORT_SAMPLE_LIMIT]]))
        if len(entries) > REPORT_SAMPLE_LIMIT:
            lines.extend([f"... and {len(entries) - REPORT_SAMPLE_LIMIT} more (see the JSON report).", ""])
    return lines or ["(none)", ""]


def render_markdown(report: MigrationReport) -> str:
    status = "succeeded" if report.succeeded else f"failed: {report.error}"
    mode = "dry run" if report.dry_run else "migration"
    images = report.images
    lines = [
        f"# Legacy world {mode}",
        "",
        f"- Legacy data: `{report.legacy_path}`",
        f"- Target: `{report.target_path}`",
        f"- Media store: {report.media_backend}",
        f"- Legacy epoch: {report.legacy_epoch}",
        f"- Started: {report.started_at.isoformat()}",
        f"- Finished: {report.finished_at.isoformat() if report.finished_at else '-'}",
        f"- Result: {status}",
        "",
        "## Legacy tables read",
        "",
        *_table(("Legacy table", "Rows"), _counts(report.source_counts)),
        "## New tables written",
        "",
        *_table(("Table", "Rows"), _counts(report.target_counts)),
        "## Conversions",
        "",
        *_table(("Conversion", "Count"), _counts(report.conversions)),
        "## Images",
        "",
        *_table(
            ("Measure", "Count"),
            [
                ("legacy rows", images.rows),
                ("linked", images.linked),
                ("objects to upload" if report.dry_run else "uploaded objects", images.uploaded),
                ("bytes to upload" if report.dry_run else "bytes uploaded", images.bytes_uploaded),
                ("deduplicated by checksum", images.deduplicated),
                ("already in the store", images.already_stored),
                ("missing files", images.missing_files),
                ("unlinked rows", images.unlinked),
                ("thumbnails skipped", images.skipped_thumbnails),
                ("files without a legacy row", images.files_without_rows),
            ],
        ),
        "## Rule overrides",
        "",
        *_table(("Legacy key", "Target", "Value", "Status"), [(rule.legacy_key, rule.target or "-", rule.value, rule.status) for rule in report.rules]),
        "## Renamed records",
        "",
        *_table(("Kind", "Legacy id", "Original", "Migrated"), [(item.kind, item.legacy_id, item.original, item.migrated) for item in report.renames]),
        "## Could not be placed",
        "",
        *_grouped(report.unplaced),
        "## Warnings",
        "",
        *_grouped(report.warnings),
        "## Tags",
        "",
        f"Free descriptive tags kept: {sum(report.free_tags.values())} uses of {len(report.free_tags)} distinct words.",
        "",
        "### Not understood",
        "",
        *_table(("Tag", "Uses"), _top(report.unknown_tags, REPORT_TOP_TAGS)),
        "### System tags kept as plain tags",
        "",
        *_table(("Tag", "Uses"), _top(report.kept_system_tags, REPORT_TOP_TAGS)),
        "## Dropped stats",
        "",
        *_table(("Stat", "Records"), _counts(report.dropped_stats)),
        "## Legacy schema differences",
        "",
        *_table(("Table", "Missing columns"), [(table, ", ".join(columns)) for table, columns in sorted(report.legacy_missing_columns.items())]),
        *_table(("Table", "Unknown columns"), [(table, ", ".join(columns)) for table, columns in sorted(report.legacy_unknown_columns.items())]),
        "## Integrity repairs",
        "",
        *_table(("Repair", "Changed"), _counts(report.repairs)),
        "## Checks",
        "",
        *_table(("Check", "Result"), [(key, value) for key, value in sorted(report.checks.items())]),
        "## Not migrated",
        "",
        *_table(("Data", "Rows"), _counts(report.not_migrated)),
    ]
    return "\n".join(lines)
