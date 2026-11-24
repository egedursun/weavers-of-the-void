import enum
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from aerona.db.tables.customs import TimeBudgetRow
from aerona.prompts.contexts.blocks import SeasonLine
from aerona.prompts.tools.mortal import MORTAL_TOOL_TEXTS
from aerona.prompts.tools.son import SON_TOOL_TEXTS
from tests.unit.test_tool_enum_lists import listed_enums, partial_lists, texts_of

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "docs" / "spec" / "17-w52-expansions.md"
SOURCE = ROOT / "backend" / "src" / "aerona"
FRONTEND = ROOT / "frontend" / "src"
SCHEMA = FRONTEND / "api" / "generated" / "schema.ts"
ROW = re.compile(r"^\| `(\w+)` \| (.+?) \| \d+ \|")
PLAIN_ROW = re.compile(r"^\| ([a-z][^|`]+?) \| (.+?) \| \d+ \|")
VALUE = re.compile(r"`(\w+)`(\s+leaves)?")
TYPED_MAP = re.compile(r"(?:Record|Partial<Record)<\s*(?:Schema\['(\w+)'\]|components\['schemas'\]\['(\w+)'\]|(\w+))\s*,")
FIELD_LISTS: dict[str, frozenset[str]] = {
    "TimeShare": frozenset(column.name for column in TimeBudgetRow.__table__.columns),
    "SeasonLine": frozenset(SeasonLine.model_fields),
}
SERVED_ELSEWHERE = {"SpeciesUse": "AnimalRole"}


@dataclass(frozen=True)
class Listed:
    name: str
    added: tuple[str, ...]
    removed: tuple[str, ...]


def script(name: str) -> ModuleType:
    found = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert found is not None and found.loader is not None
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    return module


def appendix(text: str) -> str:
    return text[text.index("## Appendix 17.A") : text.index("## Appendix 17.B")]


def listed(text: str) -> list[Listed]:
    rows: dict[str, Listed] = {}
    for line in appendix(text).splitlines():
        if match := ROW.match(line):
            pairs = VALUE.findall(re.sub(r"\([^)]*\)", "", match.group(2)))
            added = tuple(value for value, leaves in pairs if not leaves and value != match.group(1))
            removed = tuple(value for value, leaves in pairs if leaves)
            before = rows.get(match.group(1), Listed(match.group(1), (), ()))
            rows[match.group(1)] = Listed(match.group(1), before.added + added, before.removed + removed)
    return list(rows.values())


def plain_values(text: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), value)
        for line in appendix(text).splitlines()
        if (match := PLAIN_ROW.match(line))
        for value in re.findall(r"`(\w+)`", match.group(2))
    ]


def enum_classes() -> dict[str, list[type[enum.Enum]]]:
    found: dict[str, list[type[enum.Enum]]] = {}
    for path in sorted((SOURCE / "domain" / "enums").glob("*.py")):
        module = importlib.import_module(f"aerona.domain.enums.{path.stem}")
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, enum.Enum) and value.__module__ == module.__name__:
                found.setdefault(value.__name__, []).append(value)
    return found


def values_of(classes: list[type[enum.Enum]]) -> set[str]:
    return {str(member.value) for kind in classes for member in kind}


def missing_values(rows: list[Listed], classes: dict[str, list[type[enum.Enum]]]) -> list[str]:
    problems: list[str] = []
    for row in rows:
        name = SERVED_ELSEWHERE.get(row.name, row.name)
        known = values_of(classes[name]) if name in classes else FIELD_LISTS.get(name)
        if known is None:
            problems.append(f"{row.name}: no enum or typed list of that name")
            continue
        problems += [f"{row.name}.{value}: not in the code" for value in row.added if value not in known]
        problems += [f"{row.name}.{value}: should have left" for value in row.removed if value in known and name in classes]
    return problems


def unread_values(rows: list[Listed], classes: dict[str, list[type[enum.Enum]]]) -> list[str]:
    reads = script("check_enum_values_read")
    unread = set(reads.unread())
    problems: list[str] = []
    for row in rows:
        name = SERVED_ELSEWHERE.get(row.name, row.name)
        for kind in classes.get(name, []):
            members = {str(member.value): member.name for member in kind}
            problems += [f"{row.name}.{value}: never read" for value in row.added if value in members and f"{name}.{members[value]} ({value})" in unread]
    return problems


def served_lists() -> dict[str, frozenset[str]]:
    labels = script("check_label_maps")
    return {key[0].upper() + key[1:]: value for key, value in labels.enum_values(SCHEMA.read_text(encoding="utf-8")).items()}


def frontend_maps() -> list[tuple[str | None, set[str]]]:
    labels = script("check_label_maps")
    found: list[tuple[str | None, set[str]]] = []
    for path in sorted(FRONTEND.rglob("*.ts*")):
        if "generated" in path.parts or ".test." in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        for match in labels.MAP_START.finditer(text):
            if "Partial<" in (match.group(2) or ""):
                continue
            typed = TYPED_MAP.search(match.group(2) or "")
            keys = next((keys for name, keys in labels.maps_in(text[match.start() :]) if name == match.group(1)), set())
            found.append((next((group for group in typed.groups() if group), None) if typed else None, keys))
    return found


def namesake_values(name: str, added: tuple[str, ...], classes: dict[str, list[type[enum.Enum]]]) -> frozenset[str] | None:
    holders = [kind for kind in classes.get(name, []) if set(added) <= {str(member.value) for member in kind}]
    return frozenset(str(member.value) for member in holders[0]) if len(classes.get(name, [])) > 1 and holders else None


def unlabelled_values(rows: list[Listed]) -> list[str]:
    served = served_lists()
    maps = frontend_maps()
    classes = enum_classes()
    problems: list[str] = []
    for row in rows:
        name = SERVED_ELSEWHERE.get(row.name, row.name)
        values = served.get(name)
        if values is None:
            continue
        namesake = namesake_values(row.name, row.added, classes)
        if namesake is not None and not set(row.added) & values:
            values = namesake
        else:
            problems += [f"{row.name}.{value}: not served to the screens" for value in row.added if value not in values]
        keyed = [
            keys
            for typed, keys in maps
            if (typed == name and keys & values) or (typed in (None, "String") and len(keys & values) >= max(2, 0.65 * len(values)))
        ]
        problems += [f"{row.name}.{value}: no label on screen" for value in row.added if value in values and keyed and not any(value in keys for keys in keyed)]
    return problems


def unlisted_by_tools(rows: list[Listed]) -> list[str]:
    names = {SERVED_ELSEWHERE.get(row.name, row.name) for row in rows}
    kinds = [kind for kind in listed_enums() if kind.__name__ in names]
    problems: list[str] = []
    for tool in (*SON_TOOL_TEXTS.values(), *MORTAL_TOOL_TEXTS.values()):
        for field, text in texts_of(tool):
            problems += [f"{name} left out of a tool text ({field}): {', '.join(left)}" for name, left in partial_lists(text, kinds)]
    return problems


def unknown_plain_values(text: str) -> list[str]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE.rglob("*.py"))
    return [
        f"{owner}: {value} is nowhere in the code" for owner, value in plain_values(text) if not re.search(rf"['\"]{value}['\"]|\b{value.upper()}\b", source)
    ]


def test_every_value_of_appendix_17a_is_in_the_code() -> None:
    assert missing_values(listed(SPEC.read_text(encoding="utf-8")), enum_classes()) == []


def test_every_value_of_appendix_17a_is_read_by_the_engine() -> None:
    assert unread_values(listed(SPEC.read_text(encoding="utf-8")), enum_classes()) == []


def test_every_served_value_of_appendix_17a_reaches_the_screens_with_a_label() -> None:
    assert unlabelled_values(listed(SPEC.read_text(encoding="utf-8"))) == []


def test_every_tool_text_lists_every_value_of_appendix_17a_it_lists() -> None:
    assert unlisted_by_tools(listed(SPEC.read_text(encoding="utf-8"))) == []


def test_every_value_of_a_typed_list_of_appendix_17a_is_in_the_code() -> None:
    assert unknown_plain_values(SPEC.read_text(encoding="utf-8")) == []


def test_the_guard_reads_added_and_leaving_values() -> None:
    text = "## Appendix 17.A\n| `Probe` | `kept` (52.1), `gone` leaves (52.2) | 1 |\n## Appendix 17.B\n"
    assert listed(text) == [Listed("Probe", ("kept",), ("gone",))]
    probe = enum.StrEnum("Probe", {"GONE": "gone"})
    assert missing_values(listed(text), {"Probe": [probe]}) == ["Probe.kept: not in the code", "Probe.gone: should have left"]
