import argparse
import importlib
import os
import pkgutil
import re
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from export_terms import KINDS

import aerona.domain.enums
from aerona.constants.app import APP_NAME
from aerona.core.grammar import several, spoken

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "mechanics" / "game-types.md"
SIGNATURE = f'[booklet]: # "{APP_NAME} booklet: every type in the game"'
PACKAGE = aerona.domain.enums.__name__
WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|\d+")
SERVICE_MODULES = frozenset({"accounts", "job", "library", "library_jobs", "providers", "team", "telemetry"})
SERVICE_TYPES = frozenset({"ImageMime", "HealthStatus", "LedgerOperation", "TurnCounter", "PendingJobKind", "ToolBlock"})
CATALOGUES = "open_catalogues"


@dataclass(frozen=True)
class TypeList:
    module: str
    name: str
    values: tuple[str, ...]

    @property
    def title(self) -> str:
        words = WORD.findall(self.name)
        return " ".join([words[0], *(word if word.isupper() else word.lower() for word in words[1:])])


def module_title(module: str) -> str:
    return module.replace("_", " ").capitalize()


def value_label(member: Enum) -> str:
    text = spoken(member)
    return text[:1].upper() + text[1:]


def gather() -> list[TypeList]:
    found: dict[tuple[str, str], TypeList] = {}
    for info in sorted(pkgutil.iter_modules(aerona.domain.enums.__path__), key=lambda item: item.name):
        if info.name in SERVICE_MODULES:
            continue
        module = importlib.import_module(f"{PACKAGE}.{info.name}")
        for name, value in sorted(vars(module).items()):
            if not isinstance(value, type) or not issubclass(value, Enum) or value.__module__ != module.__name__:
                continue
            if name in SERVICE_TYPES or not len(value):
                continue
            found[(info.name, name)] = TypeList(info.name, name, tuple(value_label(member) for member in value))
    catalogues = [TypeList(CATALOGUES, title, tuple(spec.label for spec in table.values())) for title, table in KINDS]
    return catalogues + sorted(found.values(), key=lambda item: (item.module, item.title))


def anchor(module: str) -> str:
    return f"m-{module.replace('_', '-')}"


def lines(types: list[TypeList]) -> list[str]:
    modules = sorted({item.module for item in types}, key=lambda module: (module != CATALOGUES, module))
    values = sum(len(item.values) for item in types)
    largest = sorted(types, key=lambda item: (-len(item.values), item.title))[:20]
    out = [
        SIGNATURE,
        "",
        f"# {APP_NAME}: Every Type in the Game",
        "",
        (
            "The engine works with typed things: every kind, state, cause, role and outcome it can tell apart is a fixed list of values. "
            "This booklet counts every one of those lists and names every value in it, read straight from the game's code. "
            "The open catalogues come first: their kinds ship with the game and you can add more of your own."
        ),
        "",
        "| Types at a glance | |",
        "|---|---:|",
        f"| Type lists | {len(types):,} |",
        f"| Values across all lists | {values:,} |",
        f"| Areas of the game | {len(modules):,} |",
        "",
        "## The largest lists",
        "",
        "| Type | Area | Values |",
        "|---|---|---:|",
        *(f"| {item.title} | [{module_title(item.module)}](#{anchor(item.module)}) | {len(item.values):,} |" for item in largest),
        "",
        "## Contents",
        "",
    ]
    for module in modules:
        members = [item for item in types if item.module == module]
        lists = several(len(members), "list", "lists")
        counted = several(sum(len(item.values) for item in members), "value", "values")
        out.append(f"- [{module_title(module)}](#{anchor(module)}): {lists}, {counted}")
    out.append("")
    for module in modules:
        members = [item for item in types if item.module == module]
        out += [f'<a id="{anchor(module)}"></a>', "", f"## {module_title(module)}", ""]
        for item in members:
            out += [f"**{item.title}** ({len(item.values):,}): {', '.join(item.values)}", ""]
    return out


def ours(path: Path) -> bool:
    if not path.exists():
        return True
    with path.open(encoding="utf-8") as handle:
        return handle.readline().strip() == SIGNATURE


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the booklet that counts and names every type in the game, as one Markdown file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help=f"Markdown file to write (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    parser.add_argument("--stdout", action="store_true", help="print the Markdown instead of writing a file")
    parser.add_argument("--force", action="store_true", help="replace an existing file that this script did not write")
    arguments = parser.parse_args()
    types = gather()
    text = "\n".join(lines(types)).rstrip() + "\n"
    if arguments.stdout:
        sys.stdout.write(text)
        return 0
    output = arguments.out.resolve()
    if not arguments.force and not ours(output):
        print(f"{output} exists and was not written by this script; pass --force or choose another --out.", file=sys.stderr)
        return 2
    write_atomically(output, text)
    print(f"Wrote {output} ({several(len(types), 'type list', 'type lists')}, {several(sum(len(item.values) for item in types), 'value', 'values')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
