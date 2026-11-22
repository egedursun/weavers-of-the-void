import importlib.util
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "spec"
SPECS = (
    "13-depth-expansion.md",
    "14-cosmos-types.md",
    "16-minds-powers-living-craft.md",
    "17-w52-expansions.md",
)
GAINS = re.compile(
    r"`(?:[\w.]+\.)?([A-Z][A-Za-z]+)` gains (.*?)(?:;|(?<=[a-z`)])\.(?:\s|$)|$)"
)
VALUE = re.compile(r"`([a-z][a-z0-9_]*)`")
ASIDE = re.compile(r"\([^()]*\)")
DEFECT_ROW = re.compile(r"^\| D\d+ \|")


@dataclass(frozen=True)
class Widening:
    spec: str
    line: int
    enum: str
    value: str


def bias() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_prompt_bias", ROOT / "scripts" / "check_prompt_bias.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_prompt_bias"] = module
    spec.loader.exec_module(module)
    return module


def widenings(name: str, text: str) -> list[Widening]:
    lines = text.splitlines()
    found: list[Widening] = []
    for index, line in enumerate(lines):
        if DEFECT_ROW.match(line):
            continue
        for match in GAINS.finditer(line):
            clause = ASIDE.sub("", match.group(2))
            values = VALUE.findall(clause)
            if clause.strip().endswith(":") or not values:
                row = index + 1
                while row < len(lines) and not lines[row].startswith("|"):
                    row += 1
                while row < len(lines) and lines[row].startswith("|"):
                    values += VALUE.findall(lines[row].split("|")[1])
                    row += 1
            found.extend(
                Widening(name, index + 1, match.group(1), value)
                for value in dict.fromkeys(values)
            )
    return found


def duplicates(specs: dict[str, str]) -> list[str]:
    held: dict[str, dict[str, Widening]] = defaultdict(dict)
    problems: list[str] = []
    for name, text in specs.items():
        for item in widenings(name, text):
            first = held[item.enum].get(item.value)
            if first is not None:
                problems.append(
                    f"{item.spec}:{item.line}: {item.enum} gains {item.value} again; {first.spec}:{first.line} already adds it"
                )
            else:
                held[item.enum][item.value] = item
    return problems


def biased(specs: dict[str, str], module: ModuleType) -> list[str]:
    problems: list[str] = []
    for name, text in specs.items():
        for item in widenings(name, text):
            for finding in module.matches(
                SPEC / name,
                item.line,
                module.spaced(item.value),
                True,
                False,
                enum_value=True,
            ):
                problems.append(
                    f"{item.spec}:{item.line}: {item.enum} gains {item.value}, a word of the {finding.rule} family; name the value by what it is"
                )
    return problems


def main() -> int:
    specs = {name: (SPEC / name).read_text(encoding="utf-8") for name in SPECS}
    problems = duplicates(specs) + biased(specs, bias())
    for line in problems:
        print(line)
    print(f"spec duplicates: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
