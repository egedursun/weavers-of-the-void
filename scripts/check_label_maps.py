import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
SCHEMA = FRONTEND / "api" / "generated" / "schema.ts"
ENUM_LIST = re.compile(r"export const (\w+)Values: ReadonlyArray<[^>]*>[^=]*= \[([^\]]*)\]")
MAP_START = re.compile(r"(?:export )?const (\w+)(?::\s*(Record<[^=]+>))?\s*=\s*\{\n")
MAP_KEY = re.compile(r"\s*([a-z_][a-z0-9_-]*|'[^']+'|\"[^\"]+\")\s*(?::|,\s*$)")
NEARLY_ALL = 0.65
SMALLEST = 3


@dataclass(frozen=True)
class Gap:
    path: Path
    name: str
    enum: str
    missing: tuple[str, ...]


def enum_values(schema: str) -> dict[str, frozenset[str]]:
    return {match.group(1): frozenset(value.strip().strip("'\"") for value in match.group(2).split(",") if value.strip()) for match in ENUM_LIST.finditer(schema)}


def top_keys(body: str) -> set[str]:
    keys: set[str] = set()
    depth = 0
    for line in body.splitlines():
        if depth == 0 and (key := MAP_KEY.match(line)):
            keys.add(key.group(1).strip("'\"").replace("-", "_"))
        depth += sum(line.count(char) for char in "{[(") - sum(line.count(char) for char in "}])")
    return keys


def maps_in(text: str) -> list[tuple[str, set[str]]]:
    found: list[tuple[str, set[str]]] = []
    for match in MAP_START.finditer(text):
        depth, index = 1, match.end()
        while index < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[index], 0)
            index += 1
        if "Exclude<" not in (match.group(2) or ""):
            found.append((match.group(1), top_keys(text[match.end() : index - 1])))
    return found


def gaps_in(path: Path, enums: dict[str, frozenset[str]]) -> list[Gap]:
    gaps: list[Gap] = []
    for name, keys in maps_in(path.read_text(encoding="utf-8")):
        if len(keys) < SMALLEST:
            continue
        owners = [(enum, values) for enum, values in enums.items() if keys <= values]
        if not owners:
            continue
        enum, values = min(owners, key=lambda item: len(item[1]))
        missing = values - keys
        if missing and len(keys) / len(values) >= NEARLY_ALL:
            gaps.append(Gap(path, name, enum, tuple(sorted(missing))))
    return gaps


def main() -> int:
    enums = enum_values(SCHEMA.read_text(encoding="utf-8"))
    gaps = [gap for path in sorted(FRONTEND.rglob("*.ts*")) if "generated" not in path.parts and ".test." not in path.name for gap in gaps_in(path, enums)]
    for gap in gaps:
        print(f"{gap.path.relative_to(ROOT)}: {gap.name} labels nearly every {gap.enum} but not {', '.join(gap.missing)}")
    print(f"label maps: {len(gaps)} gap(s)")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
