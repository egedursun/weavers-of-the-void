import json
import re
from collections.abc import Mapping
from typing import Any

ELLIPSIS = "…"
SEPARATOR = " · "
LEAD_FIELDS = ("name", "title", "target_name")
PAIR = re.compile(r'"(?P<key>[A-Za-z_][\w]*)"\s*:\s*(?P<value>"(?:[^"\\]|\\.)*(?:"|$)|\[[^\]]*(?:\]|$)|[^,{}\[\]]+)')


def _is_reference(key: str) -> bool:
    return key == "id" or key.endswith(("_id", "_ids"))


def _label(key: str) -> str:
    return key.replace("_", " ")


def _flatten(arguments: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    prose: list[str] = []
    details: list[str] = []
    for key, value in arguments.items():
        if value is None or value in ("", []) or _is_reference(key):
            continue
        if isinstance(value, Mapping):
            inner_prose, inner_details = _flatten(value)
            prose.extend(inner_prose)
            details.extend(inner_details)
        elif isinstance(value, list):
            items = [str(item) for item in value if not isinstance(item, Mapping | list) and item not in (None, "")]
            if items:
                details.append(f"{_label(key)}: {', '.join(items)}")
        elif isinstance(value, bool):
            if value:
                details.append(_label(key))
        elif isinstance(value, str) and (key in LEAD_FIELDS or len(value.split()) > 1):
            prose.append(" ".join(value.split()))
        else:
            details.append(f"{_label(key)}: {value}")
    return prose, details


def describe_arguments(arguments: Mapping[str, Any]) -> str:
    leads = {key: arguments[key] for key in LEAD_FIELDS if key in arguments}
    rest = {key: value for key, value in arguments.items() if key not in LEAD_FIELDS}
    lead_prose, lead_details = _flatten(leads)
    prose, details = _flatten(rest)
    return SEPARATOR.join([*lead_prose, *prose, *lead_details, *details])


def _loose_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"'):
        truncated = len(raw) == 1 or not raw.endswith('"') or raw.endswith('\\"')
        try:
            text = json.loads(raw + '"' if truncated else raw)
        except json.JSONDecodeError:
            text = raw.strip('"')
        return f"{text}{ELLIPSIS}" if truncated and text else text
    if raw.startswith("["):
        try:
            return json.loads(raw if raw.endswith("]") else raw.rstrip(", ") + "]")
        except json.JSONDecodeError:
            return [part.strip().strip('"') for part in raw.strip("[]").split(",") if part.strip()]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _loose_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        pairs = {match["key"]: _loose_value(match["value"]) for match in PAIR.finditer(text)}
        return pairs or None
    return parsed if isinstance(parsed, dict) else None


def readable_summary(text: str | None, limit: int | None = None) -> str | None:
    if not text:
        return text
    if not text.lstrip().startswith("{"):
        return text
    arguments = _loose_object(text.strip())
    if arguments is None:
        return text
    prose = describe_arguments(arguments)
    if not prose:
        return None
    if limit is not None and len(prose) > limit:
        return prose[: limit - 1].rstrip() + ELLIPSIS
    return prose
