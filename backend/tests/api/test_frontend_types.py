import re
from pathlib import Path
from typing import Any

from aerona.main import create_app

GENERATED = Path(__file__).resolve().parents[3] / "frontend" / "src" / "api" / "generated" / "schema.ts"
KEY = re.compile(r"""['"]?([A-Za-z_][\w.:-]*)['"]?\??:""")
QUOTED = re.compile(r"""['"]([^'"\n]*)['"]""")


SCHEMA_ENTRY = re.compile(r"^    ([A-Za-z_]\w*):(.*)$")


def enum_unions(text: str) -> dict[str, set[str]]:
    unions: dict[str, set[str]] = {}
    current: str | None = None
    for line in text.split("\n"):
        entry = SCHEMA_ENTRY.match(line)
        if entry is not None:
            current = entry.group(1)
            rest = entry.group(2).strip()
            if rest.startswith("'") or rest == "":
                unions[current] = set(QUOTED.findall(rest))
            else:
                current = None
        elif current is not None and line.strip().startswith("| '"):
            unions[current] |= set(QUOTED.findall(line))
        elif current is not None and line.strip():
            current = None
    return {name: values for name, values in unions.items() if values}


def test_each_enum_is_checked_against_its_own_union() -> None:
    text = "  schemas: {\n    Boon:\n      | 'item'\n      | 'rite'\n    Trial: 'skill' | 'faith'\n    Other: {\n      title: string\n    }\n"
    assert enum_unions(text) == {"Boon": {"item", "rite"}, "Trial": {"skill", "faith"}}


def test_the_frontend_types_are_generated_from_the_api_as_it_stands() -> None:
    components: dict[str, Any] = create_app().openapi()["components"]["schemas"]
    text = GENERATED.read_text()
    keys, quoted = set(KEY.findall(text)), set(QUOTED.findall(text))
    missing = [name for name in components if name not in keys]
    unions = enum_unions(text)
    missing += [
        f"{name}.{value}"
        for name, body in components.items()
        for value in body.get("enum", [])
        if isinstance(value, str) and value not in unions.get(name, quoted)
    ]
    missing += [f"{name}.{field}" for name, body in components.items() for field in body.get("properties", {}) if field not in keys]
    assert missing == [], f"run npm run typegen in frontend: {missing[:20]}"


def test_every_error_body_is_typed_for_the_frontend() -> None:
    api: dict[str, Any] = create_app().openapi()
    assert {"ErrorResponse", "ErrorCode"} <= set(api["components"]["schemas"])
    untyped = [
        f"{method.upper()} {path}"
        for path, operations in api["paths"].items()
        if path.startswith("/api")
        for method, operation in operations.items()
        if operation["responses"].get("default", {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "").rsplit("/", 1)[-1]
        != "ErrorResponse"
    ]
    assert untyped == []
