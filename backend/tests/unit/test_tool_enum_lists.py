import enum
import importlib
import pkgutil
import re
from collections.abc import Iterator

import aerona.domain.enums as enums_package
from aerona.prompts.tools.mortal import MORTAL_TOOL_TEXTS
from aerona.prompts.tools.son import SON_TOOL_TEXTS
from aerona.prompts.tools.text import ToolText

SMALLEST_LIST = 4
NEARLY_ALL = 0.7
SEPARATORS = re.compile(r"[,;:/()]|\bor\b|\band\b|\.\s|\s(?=[a-z_]+/)")


def listed_enums() -> list[type[enum.StrEnum]]:
    found: list[type[enum.StrEnum]] = []
    for module_info in pkgutil.iter_modules(enums_package.__path__):
        module = importlib.import_module(f"{enums_package.__name__}.{module_info.name}")
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, enum.StrEnum) and value.__module__ == module.__name__ and len(value) >= SMALLEST_LIST:
                found.append(value)
    return found


def items_of(text: str) -> list[str]:
    return [item for part in SEPARATORS.split(text.lower()) if (item := " ".join(part.replace("_", " ").split()))]


def longest_run(items: list[str], values: set[str]) -> set[str]:
    best: set[str] = set()
    run: set[str] = set()
    for item in items:
        run = run | {item} if item in values else set()
        best = run if len(run) > len(best) else best
    return best


def texts_of(tool: ToolText) -> Iterator[tuple[str, str]]:
    yield "description", tool.description
    yield from tool.fields.items()


def partial_lists(text: str, kinds: list[type[enum.StrEnum]]) -> list[tuple[str, list[str]]]:
    items = items_of(text)
    spoken = {kind: {member.value.replace("_", " ") for member in kind} for kind in kinds}
    runs = {kind: longest_run(items, words) for kind, words in spoken.items()}
    whole = [words for kind, words in spoken.items() if runs[kind] == words]
    gaps: list[tuple[str, list[str]]] = []
    for kind, words in spoken.items():
        named = runs[kind]
        partial = max(SMALLEST_LIST, int(len(words) * NEARLY_ALL)) <= len(named) < len(words)
        if partial and not any(named <= other < words for other in whole):
            gaps.append((kind.__name__, [member.value for member in kind if member.value.replace("_", " ") not in named]))
    return gaps


def test_a_tool_text_that_lists_an_enum_lists_every_value_of_it() -> None:
    kinds = listed_enums()
    problems = [
        f"{tool}.{where} lists {kind} but leaves out {', '.join(missing)}"
        for texts in (SON_TOOL_TEXTS, MORTAL_TOOL_TEXTS)
        for tool, text in texts.items()
        for where, words in texts_of(text)
        for kind, missing in partial_lists(words, kinds)
    ]
    assert problems == []


def test_the_guard_finds_a_list_that_leaves_a_value_out() -> None:
    class Quarter(enum.StrEnum):
        FARMLAND = "farmland"
        MARKET = "market"
        CRAFT_QUARTER = "craft_quarter"
        HARBOUR = "harbour"
        GARDENS = "gardens"

    assert partial_lists("The district kind (farmland, market, craft_quarter, harbour)", [Quarter]) == [("Quarter", ["gardens"])]
    assert partial_lists("farmland, market, craft quarter, harbour or gardens", [Quarter]) == []

    class Foundable(enum.StrEnum):
        FARMLAND = "farmland"
        MARKET = "market"
        CRAFT_QUARTER = "craft_quarter"
        HARBOUR = "harbour"

    assert partial_lists("farmland, market, craft_quarter or harbour", [Quarter, Foundable]) == []
    assert partial_lists("farmland, then market, then craft_quarter, the harbour", [Quarter]) == []
