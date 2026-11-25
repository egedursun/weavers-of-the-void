import dataclasses
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import Field

from aerona.core.grammar import several, spoken
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.explorer import links_of
from aerona.engine.interconnect.registry import Mechanic
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.model import RuleDescriptor, rule_meta
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.lexical import folded, ranked
from aerona.tools.divine_will.paging import failed, paged, paged_hits, plain

W = DivineWillToolId
MECHANICS = frozenset({Toolset.MECHANICS})
RULE_READING = frozenset({Toolset.MECHANICS, Toolset.RULES_READ})
GAME_RULES = Path(__file__).resolve().parents[5] / "docs" / "game-rules.md"
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ANCHOR = re.compile(r'<a id="[^"]*"></a>')
PATH_JOIN = " > "
LABEL_WEIGHT = 4
PATH_WEIGHT = 4
GROUP_WEIGHT = 2
TITLE_WEIGHT = 4
KEY_WEIGHT = 4
DETAIL_WEIGHT = 1


class SearchRulesInput(PagedInput):
    query: str = Field(default="", max_length=300)
    group: str = Field(default="", max_length=80)


class ReadRuleInput(PagedInput):
    namespace: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)


class SearchMechanicsInput(PagedInput):
    query: str = Field(default="", max_length=300)


class ReadMechanicInput(PagedInput):
    key: str = Field(min_length=1, max_length=160)


class ReadGameRulesInput(PagedInput):
    section: str = Field(default="", max_length=200)


@cache
def units() -> dict[str, str]:
    defaults = Rules()
    found: dict[str, str] = {}
    for part in dataclasses.fields(defaults):
        for definition in dataclasses.fields(getattr(defaults, part.name)):
            found[f"{part.name}.{definition.name}"] = rule_meta(definition).unit
    return found


def rule_fields(rule: RuleDescriptor) -> list[tuple[str, int]]:
    return [(rule.label, LABEL_WEIGHT), (rule.path.replace("_", " "), PATH_WEIGHT), (rule.group, GROUP_WEIGHT)]


def rule_line(rule: RuleDescriptor) -> str:
    unit = units().get(rule.path, "")
    changed = "" if rule.value == rule.default else f" (default {plain(rule.default)})"
    return f"- {rule.path} = {plain(rule.value)}{f' {unit}' if unit else ''}{changed} · range {plain(rule.minimum)} to {plain(rule.maximum)} · {rule.label}"


async def search_rules(call: WillCall, query: SearchRulesInput) -> WillResult:
    rules = catalog(call.rules)
    if query.group:
        groups = sorted({rule.group for rule in rules})
        if query.group not in groups:
            return failed(f"No rule group called {query.group}. Groups: {', '.join(groups)}.")
        rules = [rule for rule in rules if rule.group == query.group]
    hits = [rule_line(rule) for rule in ranked(query.query, rules, rule_fields)]
    return await paged_hits(call, W.SEARCH_RULES, query, hits, empty="No rule matches. Try other words.")


def coupled(path: str) -> list[Mechanic]:
    return [mechanic for mechanic in REGISTERED.values() if any(coupling.rule_key == path for coupling in mechanic.couplings)]


async def read_rule(call: WillCall, query: ReadRuleInput) -> WillResult:
    path = f"{query.namespace}.{query.name}"
    rule = next((item for item in catalog(call.rules) if item.path == path), None)
    if rule is None:
        near = ranked(f"{query.namespace} {query.name}", catalog(call.rules), rule_fields)[:5]
        hint = f" Nearest: {', '.join(item.path for item in near)}." if near else ""
        return failed(f"There is no rule {path}.{hint}")
    unit = units().get(path, "")
    lines = [
        f"# {rule.path}",
        rule.label,
        f"value: {plain(rule.value)}{f' {unit}' if unit else ''}",
        f"default: {plain(rule.default)} · range {plain(rule.minimum)} to {plain(rule.maximum)} · group {rule.group}",
        "This world keeps its own value." if rule.value != rule.default else "This world uses the default.",
    ]
    if rule.warning:
        lines.append(rule.warning)
    tied = coupled(path)
    if tied:
        lines.append(f"## Mechanics it steers ({several(len(tied), 'mechanic', 'mechanics')})")
        lines += [f"- {mechanic.key} · {mechanic.title} · {spoken(mechanic.subsystem)}" for mechanic in tied]
    return await paged(call, W.READ_RULE, query, lines, empty="")


def mechanic_fields(mechanic: Mechanic) -> list[tuple[str, int]]:
    detail = " ".join((*mechanic.phases, *mechanic.tables, *mechanic.tools, *mechanic.levers, *mechanic.fields, mechanic.spec_item))
    return [
        (mechanic.title, TITLE_WEIGHT),
        (mechanic.key.replace("_", " ").replace(".", " "), KEY_WEIGHT),
        (mechanic.subsystem.value, GROUP_WEIGHT),
        (detail, DETAIL_WEIGHT),
    ]


def mechanic_line(mechanic: Mechanic) -> str:
    return f"- {mechanic.key} · {mechanic.title} · {spoken(mechanic.subsystem)} · {several(len(mechanic.phases), 'phase', 'phases')}"


async def search_mechanics(call: WillCall, query: SearchMechanicsInput) -> WillResult:
    mechanics = sorted(REGISTERED.values(), key=lambda item: item.key)
    hits = [mechanic_line(mechanic) for mechanic in ranked(query.query, mechanics, mechanic_fields)]
    return await paged_hits(call, W.SEARCH_MECHANICS, query, hits, empty="No mechanic matches. Try other words.")


def listed(label: str, values: tuple[str, ...]) -> list[str]:
    return [f"{label}: {', '.join(values)}"] if values else []


async def read_mechanic(call: WillCall, query: ReadMechanicInput) -> WillResult:
    mechanic = REGISTERED.get(query.key)
    if mechanic is None:
        near = ranked(query.key, sorted(REGISTERED.values(), key=lambda item: item.key), mechanic_fields)[:5]
        hint = f" Nearest: {', '.join(item.key for item in near)}." if near else ""
        return failed(f"There is no mechanic {query.key}.{hint}")
    lines = [
        f"# {mechanic.key} · {mechanic.title}",
        f"subsystem: {spoken(mechanic.subsystem)} · spec item {mechanic.spec_item} · seen through {spoken(mechanic.exposure)}",
    ]
    lines += listed("epoch phases", mechanic.phases)
    lines += listed("tables", mechanic.tables)
    lines += listed("fields", mechanic.fields)
    lines += listed("flows", mechanic.flows)
    lines += listed("incident kinds", mechanic.templates)
    lines += listed("agent tools", mechanic.tools)
    lines += listed("god levers", mechanic.levers)
    lines += listed("targets", mechanic.targets)
    if mechanic.backfill:
        lines.append(f"backfill: {mechanic.backfill}")
    if mechanic.isolated_reason:
        lines.append(f"stands alone because: {mechanic.isolated_reason}")
    for coupling in mechanic.couplings:
        rule = f" under rule {coupling.rule_key}" if coupling.rule_key else ""
        lines.append(f"- couples to {spoken(coupling.target)} through {coupling.carrier} ({spoken(coupling.kind)}){rule}")
    links = links_of(mechanic.key)
    if links:
        lines.append(f"## Links ({several(len(links), 'link', 'links')})")
        lines += [
            f"- {'feeds' if link.direction == 'out' else 'fed by'} {link.other or 'the world'}"
            + (f" ({spoken(link.other_subsystem)})" if link.other_subsystem is not None else "")
            + f" · {spoken(link.kind)} · through {', '.join(link.carriers)}"
            for link in links
        ]
    return await paged(call, W.READ_MECHANIC, query, lines, empty="")


@cache
def booklet() -> tuple[str, ...]:
    return tuple(GAME_RULES.read_text(encoding="utf-8").splitlines()) if GAME_RULES.is_file() else ()


@dataclass(frozen=True)
class Heading:
    line: int
    level: int
    title: str
    path: str


@cache
def headings() -> tuple[Heading, ...]:
    found: list[Heading] = []
    trail: list[tuple[int, str]] = []
    for index, line in enumerate(booklet()):
        match = HEADING.match(line)
        if not match:
            continue
        level, title = len(match.group(1)), ANCHOR.sub("", match.group(2)).strip()
        trail = [*(item for item in trail if item[0] < level), (level, title)]
        found.append(Heading(index, level, title, PATH_JOIN.join(name for _, name in trail)))
    return tuple(found)


def section_body(position: int) -> list[str]:
    marks = headings()
    mark = marks[position]
    end = next((other.line for other in marks[position + 1 :] if other.level <= mark.level), len(booklet()))
    body = "\n".join(ANCHOR.sub("", line) for line in booklet()[mark.line : end])
    return [block for block in body.split("\n\n") if block.strip()]


def section_text(title: str) -> list[str] | None:
    wanted = folded(title).strip().lstrip("#").strip()
    marks = headings()
    exact = [position for position, mark in enumerate(marks) if folded(mark.path) == wanted]
    chosen = exact or [position for position, mark in enumerate(marks) if folded(mark.title) == wanted]
    if not chosen:
        return None
    return [block for position in chosen for block in (f"[{marks[position].path}]", *section_body(position))]


async def read_game_rules(call: WillCall, query: ReadGameRulesInput) -> WillResult:
    if not booklet():
        return failed("The rules booklet is not on this server.")
    if not query.section:
        lines = [f"{'  ' * (mark.level - 1)}- {mark.path}" for mark in headings()]
        head = "The sections of the rules booklet. Read one with its path (or its title, which reads every section of that title) as section."
        return await paged(call, W.READ_GAME_RULES, query, lines, head=head, empty="")
    blocks = section_text(query.section)
    if blocks is None:
        near = [mark.path for mark in ranked(query.section, headings(), lambda mark: [(mark.path, 1)])[:5]]
        hint = f" Nearest: {'; '.join(near)}." if near else ""
        return failed(f"No section titled {query.section}.{hint}")
    return await paged(call, W.READ_GAME_RULES, query, blocks, empty="")


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.SEARCH_RULES, RULE_READING, SearchRulesInput, search_rules),
        WillTool(W.READ_RULE, RULE_READING, ReadRuleInput, read_rule),
        WillTool(W.SEARCH_MECHANICS, MECHANICS, SearchMechanicsInput, search_mechanics),
        WillTool(W.READ_MECHANIC, MECHANICS, ReadMechanicInput, read_mechanic),
        WillTool(W.READ_GAME_RULES, MECHANICS, ReadGameRulesInput, read_game_rules),
    ]
