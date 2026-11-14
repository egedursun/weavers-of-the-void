import re
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from aerona.domain import enums

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
TALLY = re.compile(r"@dataclass\nclass (\w+Tally)[^:]*:\n((?:    \w+: [^\n]+\n)+)")
WRITES = (
    re.compile(r"\.(\w+)\s*(?:\+=|-=|\*=|/=|=(?!=))"),
    re.compile(r"\b(\w+)=(?!=)"),
    re.compile(r"\.(\w+)\["),
    re.compile(r"\.(\w+)\.(?:append|add|update|extend)\("),
    re.compile(r"\.(\w+)\.\w+\s*\+="),
)


def enum_values() -> set[str]:
    found: set[str] = set()
    for module in iter_modules(enums.__path__):
        for value in vars(import_module(f"{enums.__name__}.{module.name}")).values():
            if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum:
                found |= {str(member.value) for member in value}
    return found


def test_every_tally_field_is_counted_somewhere() -> None:
    sources = {path: path.read_text() for path in ENGINE.rglob("*.py")}
    written = {name for text in sources.values() for pattern in WRITES for name in pattern.findall(text)}
    dynamic = enum_values()
    missing = [
        f"{path.relative_to(ENGINE)}:{name}.{field}"
        for path, text in sources.items()
        for name, body in TALLY.findall(text)
        for field in re.findall(r"    (\w+): ", body)
        if field not in written and not ("setattr(tally" in text and field in dynamic)
    ]
    assert missing == [], f"a tally field nothing counts reports a zero forever; count it where it happens or remove it: {missing}"
