from typing import Any

from aerona.migration.legacy.report import MigrationReport

CLAMPED = "clamped value"
TRUNCATED = "truncated text"


def as_int(value: Any) -> int | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


Limits = tuple[int, int | None]


def bounded(report: MigrationReport, reference: str, label: str, value: int | None, limits: Limits) -> int | None:
    if value is None:
        return None
    low, high = limits
    result = max(low, value) if high is None else max(low, min(high, value))
    if result != value:
        report.warn(CLAMPED, reference, f"{label} {value} moved into range ({result})")
    return result


def required_bounded(report: MigrationReport, reference: str, label: str, value: int | None, limits: Limits, *, fallback: int) -> int:
    result = bounded(report, reference, label, value, limits)
    return fallback if result is None else result


def truncated(report: MigrationReport, reference: str, label: str, text: str | None, limit: int) -> str | None:
    if text is None or len(text) <= limit:
        return text
    report.warn(TRUNCATED, reference, f"{label} cut from {len(text)} to {limit} characters")
    return text[:limit]
