import re
from pathlib import Path
from typing import Any

from aerona.main import create_app

GENERATED = Path(__file__).resolve().parents[3] / "frontend" / "src" / "api" / "generated" / "schema.ts"
KEY = re.compile(r"""['"]?([A-Za-z_][\w.:-]*)['"]?\??:""")
QUOTED = re.compile(r"""['"]([^'"\n]*)['"]""")


def test_the_frontend_types_are_generated_from_the_api_as_it_stands() -> None:
    components: dict[str, Any] = create_app().openapi()["components"]["schemas"]
    text = GENERATED.read_text()
    keys, quoted = set(KEY.findall(text)), set(QUOTED.findall(text))
    missing = [name for name in components if name not in keys]
    missing += [f"{name}.{value}" for name, body in components.items() for value in body.get("enum", []) if isinstance(value, str) and value not in quoted]
    missing += [f"{name}.{field}" for name, body in components.items() for field in body.get("properties", {}) if field not in keys]
    assert missing == [], f"run npm run typegen in frontend: {missing[:20]}"
