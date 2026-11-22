import argparse
import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import get_args

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import EntityStats
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import (
    GENERIC_CARRIERS,
    flow_carriers,
    flow_pairs,
    mechanic_reads,
    mechanic_writes,
    structural_edges,
)
from aerona.engine.interconnect.registry import Edge, EdgeKind

assert tables

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "spec" / "13-depth-metric.md"
SPEC = ROOT / "docs" / "spec" / "13-depth-expansion.md"
STAT_MODELS = {
    model.model_fields["kind"].default: model
    for model in get_args(get_args(EntityStats)[0])
}
NODE_TABLES = {
    "son": SonRow,
    "creator": CreatorRow,
    "foreign_god": ForeignGodRow,
    "war": WarRow,
    "world": WorldRow,
    "star": StarRow,
    "route": RouteRow,
}
TARGET_SECTIONS = ("J.7", "J.10", "J.12", "J.13", "J.14", "J.15", "J.17", "J.18")
TARGET_NUMBER = re.compile(r"~?(\d+)")
TARGET_INCREMENT = re.compile(r"^\+\s*~?(\d+)")
TARGET_ALIASES = {
    "route / journey": ("route",),
    "region and world": ("region", "world"),
}
TARGET_COLUMNS = 3
ENGINE_ROOT = ROOT / "backend" / "src" / "aerona" / "engine"
CROSS_SUBSYSTEM_ONLY = True
LOCK_COLUMN = "locked"
TYPE_TABLES: dict[str, tuple[str, ...]] = {
    "vessel": ("vessel_profiles", "vessel_sections", "ship_crews", "ship_states"),
    "language": (
        "language_profiles",
        "language_grammar",
        "language_intelligibility",
        "language_policies",
        "language_registers",
        "language_standing",
        "lexemes",
        "scripts",
        "sound_changes",
    ),
    "title": ("title_profiles", "title_holders"),
    "phenomenon": ("phenomenon_profiles", "phenomenon_footprints"),
    "natural_law": ("natural_law_profiles", "natural_law_exceptions", "law_theories"),
    "beast": ("beast_profiles", "creature_anatomy", "creature_attacks"),
    "theory": ("theory_profiles", "theory_adherents", "theory_anomalies"),
    "art_form": ("art_form_profiles", "art_form_practitioners"),
    "celestial": ("celestial_readings",),
    "structure": (
        "structure_profiles",
        "structure_sections",
        "structure_staff",
        "structure_ley",
    ),
}


@dataclass(frozen=True)
class Row:
    name: str
    a: int
    b: int
    c: int
    targets: tuple[int, int, int] | None


def node_types() -> list[str]:
    return [*(entity_type.value for entity_type in EntityType), *NODE_TABLES]


def typed_fields(name: str) -> set[str]:
    if name in NODE_TABLES:
        return {
            column.key
            for column in NODE_TABLES[name].__table__.columns
            if not column.primary_key
        }
    model = STAT_MODELS.get(name)
    return (
        set()
        if model is None
        else {field for field in model.model_fields if field != "kind"}
    )


@cache
def class_attribute_reads() -> dict[str, frozenset[str]]:
    classes = {mapper.class_.__name__ for mapper in Base.registry.mappers}
    found: dict[str, set[str]] = {}
    for path in sorted(ENGINE_ROOT.rglob("*.py")):
        if "interconnect" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        named = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        attributes = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)
        }
        for cls in named & classes:
            found.setdefault(cls, set()).update(attributes)
    return {name: frozenset(values) for name, values in found.items()}


def engine_attribute_reads() -> dict[str, frozenset[str]]:
    reads = class_attribute_reads()
    return {
        name: reads.get(table.__name__, frozenset())
        for name, table in NODE_TABLES.items()
    }


def read_columns(name: str) -> set[str]:
    return typed_fields(name) & engine_attribute_reads().get(name, frozenset())


@cache
def table_classes() -> dict[str, str]:
    return {
        str(mapper.class_.__tablename__): mapper.class_.__name__
        for mapper in Base.registry.mappers
    }


def keyed_by(table_name: str) -> frozenset[str]:
    return frozenset(
        name
        for name, table in Base.metadata.tables.items()
        if name != table_name
        and any(
            foreign.column.table.name == table_name
            for column in table.primary_key.columns
            for foreign in column.foreign_keys
        )
    )


@cache
def owned_tables(name: str) -> frozenset[str]:
    if name in NODE_TABLES:
        own = str(NODE_TABLES[name].__tablename__)
        return frozenset({own}) | keyed_by(own)
    return frozenset(TYPE_TABLES.get(name, ()))


def owned_columns(name: str) -> set[str]:
    reads = class_attribute_reads()
    node_table = str(NODE_TABLES[name].__tablename__) if name in NODE_TABLES else None
    found: set[str] = set()
    for table_name in sorted(owned_tables(name) - {node_table}):
        table = Base.metadata.tables[table_name]
        columns = {
            column.key
            for column in table.columns
            if not column.primary_key and column.key != LOCK_COLUMN
        }
        found |= {
            f"{table_name}.{column}"
            for column in columns
            & reads.get(table_classes().get(table_name, ""), frozenset())
        }
    return found


def target_names(raw: str) -> tuple[str, ...]:
    name = raw.replace("(new)", "").strip().lower()
    return TARGET_ALIASES.get(name, (name.replace(" ", "_"),))


def last_number(cell: str) -> int | None:
    tail = cell.rsplit("→", 1)[-1]
    found = TARGET_NUMBER.search(tail)
    return int(found.group(1)) if found is not None else None


def spec_section(text: str, heading: str) -> str:
    start = text.index(f"### {heading} ")
    end = text.find("\n### ", start + 1)
    return text[start : end if end >= 0 else len(text)]


def spec_targets() -> dict[str, tuple[int, int, int]]:
    text = SPEC.read_text(encoding="utf-8")
    known = set(node_types())
    found: dict[str, tuple[int, int, int]] = {}
    for heading in TARGET_SECTIONS:
        for line in spec_section(text, heading).splitlines():
            cells = (
                [cell.strip() for cell in line.strip().strip("|").split("|")]
                if line.startswith("| ")
                else []
            )
            if (
                not cells
                or cells[0] in ("Entity", "Wave")
                or cells[0].startswith("---")
            ):
                continue
            names = [name for name in target_names(cells[0]) if name in known]
            if len(cells) == TARGET_COLUMNS + 1:
                numbers = [last_number(cell) for cell in cells[1:]]
                if all(number is not None for number in numbers):
                    for name in names:
                        found[name] = (
                            int(numbers[0] or 0),
                            int(numbers[1] or 0),
                            int(numbers[2] or 0),
                        )
            elif (
                len(cells) == 2
                and (increment := TARGET_INCREMENT.match(cells[1])) is not None
            ):
                for name in names:
                    a, b, c = found.get(name, (0, 0, 0))
                    found[name] = (a + int(increment.group(1)), b, c)
    return found


def subsystem_pairs(edges: Iterable[Edge]) -> set[tuple[str, str]]:
    return {
        (edge.source.value, edge.target.value)
        for edge in edges
        if not CROSS_SUBSYSTEM_ONLY or edge.source is not edge.target
    }


def measure() -> list[Row]:
    edges = structural_edges()
    carriers = [carrier for carrier in flow_carriers() if carrier not in GENERIC_CARRIERS]
    targets = spec_targets()
    rows: list[Row] = []
    for name in node_types():
        prefix = f"{name}."
        own = {f"table.{table}" for table in owned_tables(name)}
        read = {
            key
            for mechanic in REGISTERED.values()
            for key in mechanic_reads(mechanic)
            if key.startswith(prefix)
        }
        acting = [
            mechanic
            for mechanic in REGISTERED.values()
            if name in mechanic.targets
            or any(key.startswith(prefix) for key in mechanic_writes(mechanic))
            or own & (mechanic_writes(mechanic) | mechanic_reads(mechanic))
        ]
        declared = {field for mechanic in acting for field in mechanic.fields}
        attributes = (
            {key.removeprefix(prefix) for key in read}
            | declared
            | (read_columns(name) if name in NODE_TABLES else set())
            | owned_columns(name)
        )
        keys = {mechanic.key for mechanic in acting}
        carried = subsystem_pairs(
            edge
            for edge in edges
            if edge.kind is not EdgeKind.RULE_SWITCH
            and edge.carrier not in GENERIC_CARRIERS
            and (
                edge.carrier.startswith(prefix)
                or (edge.carrier.startswith("table.") and edge.writer in keys)
            )
        ) | {
            (source.value, target.value)
            for carrier in carriers
            if carrier.startswith(prefix) or carrier.startswith("table.")
            for writer, source, target in flow_pairs(carrier)
            if (carrier.startswith(prefix) or writer in keys)
            and (not CROSS_SUBSYSTEM_ONLY or source is not target)
        }
        rows.append(
            Row(name, len(attributes), len(keys), len(carried), targets.get(name))
        )
    return rows


def mark(value: int, target: int | None) -> str:
    if target is None:
        return f"{value}"
    return f"{value} / {target} {'met' if value >= target else 'short'}"


def shortfalls(rows: list[Row]) -> list[str]:
    found: list[str] = []
    for row in rows:
        if row.targets is None:
            continue
        for label, value, target in zip(
            ("attributes read", "mechanics acting", "subsystem pairs"),
            (row.a, row.b, row.c),
            row.targets,
            strict=True,
        ):
            if value < target:
                found.append(f"{row.name}: {label} {value} below its target {target}")
    return found


def render(rows: list[Row]) -> str:
    lines = [
        "# Depth metric",
        "",
        "Generated by `scripts/depth_metric.py` (spec 13, section 0.2 and J.7) from the `@reads`/`@writes` annotations and the interconnection registry.",
        "A counts the typed attributes of the type: those the mechanics acting on it declare, and its stats, node-table columns and the columns of the tables that hold its own rows that engine code reads,",
        "B the registered mechanics that act on the type (they target it, or their phases write its attributes, or read or write its node table or a table of its own rows),",
        "and C the distinct source subsystem to target subsystem pairs the type carries.",
        "Targets are the latest of J.7, J.10, J.12-J.15 and J.17-J.18; where one is set the cell shows value / target and whether it is met.",
        "",
        "| Node type | A | B | C |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        a, b, c = row.targets if row.targets is not None else (None, None, None)
        lines.append(
            f"| {row.name} | {mark(row.a, a)} | {mark(row.b, b)} | {mark(row.c, c)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("write", "print", "check"), nargs="?", default="print"
    )
    mode = parser.parse_args().mode
    rows = measure()
    text = render(rows)
    if mode == "write":
        OUTPUT.write_text(text, encoding="utf-8")
        print(f"written to {OUTPUT.relative_to(ROOT)}")
    elif mode == "check":
        failed = False
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
            print(
                f"{OUTPUT.relative_to(ROOT)} is stale: run scripts/depth_metric.py write"
            )
            failed = True
        for line in shortfalls(rows):
            print(line)
            failed = True
        return 1 if failed else 0
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
