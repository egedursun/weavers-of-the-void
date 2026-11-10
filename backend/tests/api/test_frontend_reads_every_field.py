import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.main import create_app

FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src"
WORD = re.compile(r"[A-Za-z_][\w]*")
SHOWN_BESIDE = ("_label", "_caption")
NAMED_BY = ("", "_name", "_label")
ID_SUFFIXES = ("_entity_id", "_node_id", "_id")
STAT_GRID = ("EntityRecord", "stats")


def is_app_source(path: Path) -> bool:
    return path.is_file() and "generated" not in path.parts and ".test." not in path.name and "ixtures" not in path.name and "test-utils" not in path.parts


def read_words() -> set[str]:
    return {word for path in FRONTEND.rglob("*.ts*") if is_app_source(path) for word in WORD.findall(path.read_text(encoding="utf-8"))}


def refs(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value.rsplit("/", 1)[-1]
            else:
                yield from refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from refs(value)


def served_models(api: dict[str, Any]) -> set[str]:
    schemas: dict[str, Any] = api["components"]["schemas"]
    replies = [
        body for operations in api["paths"].values() if "get" in operations for code, body in operations["get"]["responses"].items() if code.startswith("2")
    ]
    stack = [name for body in replies for name in refs(body)]
    seen: set[str] = set()
    while stack:
        name = stack.pop()
        if name in seen or name not in schemas:
            continue
        seen.add(name)
        stack.extend(refs(schemas[name]))
    return seen


def vocabulary(body: dict[str, Any]) -> str | None:
    item = body.get("items", {}).get("$ref", "")
    name = item.rsplit("/", 1)[-1]
    return f"{name[:1].lower()}{name[1:]}Values" if name else None


def shown(field: str, fields: dict[str, Any], words: set[str]) -> bool:
    if vocabulary(fields[field]) in words:
        return True
    if field in words or any(f"{field}{suffix}" in fields and f"{field}{suffix}" in words for suffix in SHOWN_BESIDE):
        return True
    if field.endswith("_key") and field.removesuffix("_key") in fields and field.removesuffix("_key") in words:
        return True
    bases = {field.removesuffix(suffix) for suffix in ID_SUFFIXES if field.endswith(suffix)}
    return any(f"{base}{suffix}" in fields and f"{base}{suffix}" in words for base in bases for suffix in NAMED_BY)


def grid_models(api: dict[str, Any]) -> set[str]:
    owner, field = STAT_GRID
    return set(refs(api["components"]["schemas"].get(owner, {}).get("properties", {}).get(field, {})))


def unshown(api: dict[str, Any], words: set[str], grid_keys: frozenset[str] = frozenset()) -> list[str]:
    schemas: dict[str, Any] = api["components"]["schemas"]
    grid = grid_models(api)
    fields = {name: schemas[name].get("properties", {}) for name in sorted(served_models(api))}
    return [
        f"{name}.{field}" for name, props in fields.items() for field in props if not shown(field, props, words) and not (name in grid and field in grid_keys)
    ]


def test_a_stat_of_an_entity_is_shown_by_the_stat_grid_when_the_catalogue_lists_it() -> None:
    api = {
        "paths": {"/api/entities/{id}": {"get": {"responses": {"200": {"$ref": "#/components/schemas/EntityRecord"}}}}},
        "components": {
            "schemas": {
                "EntityRecord": {"properties": {"stats": {"oneOf": [{"$ref": "#/components/schemas/LawStats"}]}}},
                "LawStats": {"properties": {"rigidity": {}, "secret_weight": {}}},
            }
        },
    }
    assert unshown(api, {"stats"}, frozenset({"rigidity"})) == ["LawStats.secret_weight"]


def test_a_field_counts_as_shown_through_its_label_or_the_record_it_names() -> None:
    api = {
        "paths": {"/api/wars": {"get": {"responses": {"200": {"$ref": "#/components/schemas/WarView"}, "422": {"$ref": "#/components/schemas/Error"}}}}},
        "components": {
            "schemas": {
                "WarView": {
                    "properties": {
                        "kind": {},
                        "kind_label": {},
                        "target_id": {},
                        "target": {},
                        "maker_entity_id": {},
                        "maker_name": {},
                        "rival_id": {},
                        "omen": {},
                        "reason": {},
                        "reason_key": {},
                        "clash": {"$ref": "#/components/schemas/Clash"},
                        "kinds": {"items": {"$ref": "#/components/schemas/WarKind"}},
                    }
                },
                "Clash": {"properties": {"epoch": {}, "losses": {}}},
                "Error": {"properties": {"detail": {}}},
            }
        },
    }
    words = {"kind_label", "target", "clash", "epoch", "reason", "maker_name"}
    assert unshown(api, {*words, "warKindValues"}) == ["Clash.losses", "WarView.rival_id", "WarView.omen"]
    assert unshown(api, words) == ["Clash.losses", "WarView.rival_id", "WarView.omen", "WarView.kinds"]


def test_every_value_the_api_serves_is_read_by_a_screen() -> None:
    stat_keys = frozenset(stat.key for spec in ENTITY_TYPES.values() for stat in spec.stats)
    missing = unshown(create_app().openapi(), read_words(), stat_keys)
    assert missing == [], f"{len(missing)} served values no screen reads; show each or stop serving it: {missing}"
