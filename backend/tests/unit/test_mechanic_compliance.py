import re
from functools import cache
from pathlib import Path

from aerona.db.base import Base
from aerona.engine.interconnect.annotations import declared_writes
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.compliance import CATALOGUE
from aerona.engine.interconnect.flows import PHASE_FLOWS
from aerona.engine.interconnect.guards import CONSERVED_KEYS
from aerona.engine.interconnect.registry import Exposure
from aerona.engine.interconnect.table_backfills import TABLE_BACKFILLS, table_backfill
from aerona.engine.pipeline import PHASE_REGISTRY
from aerona.prompts.ids import PromptId
from aerona.prompts.tools.ids import MortalToolId, SonToolId
from aerona.services.player.catalog import ACTIONS_BY_ID

ROOT = Path(__file__).resolve().parents[3]
MATRICES = tuple(ROOT / "docs" / "spec" / f"{number}-coverage.md" for number in (13, 16, 17))
FRONTEND = ROOT / "frontend" / "src"
GENERIC_LEVERS = ("lever:pin", "lever:unpin", "lever:suppress", "lever:unsuppress", "lever:run", "modifier:add", "modifier:remove")


def matrix_ids() -> set[str]:
    lines = [line for matrix in MATRICES for line in matrix.read_text(encoding="utf-8").splitlines()]
    return {line.split("|")[1].strip() for line in lines if line.startswith("| ") and not line.startswith("| ID ")}


def frontend_source() -> str:
    paths = [*FRONTEND.rglob("*.tsx"), *FRONTEND.rglob("*.ts")]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file() and "generated" not in path.parts)


def test_every_tool_mechanic_that_owns_no_table_names_the_god_levers_that_govern_it() -> None:
    silent = [key for key, mechanic in REGISTERED.items() if mechanic.tools and not mechanic.tables and not mechanic.levers]
    unknown = [(key, lever) for key, mechanic in REGISTERED.items() for lever in mechanic.levers if lever not in ACTIONS_BY_ID]
    assert silent == []
    assert unknown == []


def test_generic_levers_exist_for_every_mechanic() -> None:
    assert [action for action in GENERIC_LEVERS if action not in ACTIONS_BY_ID] == []


def test_every_registered_mechanic_is_traceable_and_complete() -> None:
    ids = matrix_ids()
    source = frontend_source()
    tables = set(Base.metadata.tables)
    problems: list[str] = []
    for key, mechanic in REGISTERED.items():
        if mechanic.spec_item not in ids:
            problems.append(f"{key}: spec item {mechanic.spec_item} is not in the coverage matrix")
        problems.extend(f"{key}: unknown phase {phase}" for phase in mechanic.phases if phase not in PHASE_REGISTRY)
        if not mechanic.surface.keys:
            problems.append(f"{key}: no UI surface")
        problems.extend(f"{key}: UI surface {surface} is not rendered by the frontend" for surface in mechanic.surface.keys if surface not in source)
        if not mechanic.backfill.strip():
            problems.append(f"{key}: no backfill rule")
        problems.extend(f"{key}: unknown table {table}" for table in mechanic.tables if table not in tables)
    assert problems == [], "\n".join(problems)


def test_every_engine_step_is_claimed_by_a_registered_mechanic() -> None:
    claimed = {phase for mechanic in REGISTERED.values() for phase in mechanic.phases}
    assert [name for name in PHASE_REGISTRY if name not in claimed] == []


BACKEND = ROOT / "backend" / "src" / "aerona"
VERSIONS = BACKEND / "db" / "alembic" / "versions"
PLAIN_BACKFILLS = ("none", "computed", "existing mechanic")


@cache
def backend_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in BACKEND.rglob("*.py") if "alembic" not in path.parts)


def template_written(template: str, source: str) -> bool:
    if f'"{template}"' in source or f'"{template}' in source:
        return True
    return any(template.startswith(prefix) for prefix in written_prefixes(source))


@cache
def written_prefixes(source: str) -> frozenset[str]:
    return frozenset(re.findall(r'f"([a-z_.]+)\{', source))


@cache
def fixup_keys() -> frozenset[str]:
    return frozenset(re.findall(r'_FIXUP = "([a-z0-9_.]+)"', backend_source()))


def backfill_known(text: str) -> bool:
    head = text.split(":", 1)[0].strip()
    if head in PLAIN_BACKFILLS or head in PHASE_REGISTRY or head in fixup_keys():
        return True
    revision = head.removeprefix("migration ").strip()
    return head.startswith("migration ") and any(VERSIONS.glob(f"{revision}_*.py"))


def test_the_generic_layer_holds_for_every_mechanic() -> None:
    source = backend_source()
    tools = {item.value for item in SonToolId} | {item.value for item in MortalToolId}
    problems: list[str] = []
    for key, mechanic in REGISTERED.items():
        if not mechanic.phases:
            problems.append(f"{key}: no step, so it can be neither run now nor suppressed")
        problems.extend(f"{key}: template {template} is never written" for template in mechanic.templates if not template_written(template, source))
        if mechanic.exposure is Exposure.TOOL and not mechanic.tools:
            problems.append(f"{key}: exposed as a tool but names none")
        problems.extend(f"{key}: unknown tool {tool}" for tool in mechanic.tools if tool not in tools)
        if mechanic.exposure is Exposure.CONTEXT and not mechanic.targets:
            problems.append(f"{key}: exposed in context but acts on nobody")
        if not backfill_known(mechanic.backfill):
            problems.append(f"{key}: backfill {mechanic.backfill[:40]} is not a step, fix-up, migration or plain rule")
        for name in mechanic.phases:
            conserved = {item for item in declared_writes(PHASE_REGISTRY[name].run) if item.split(".")[-1] in CONSERVED_KEYS and not item.startswith("table.")}
            if conserved and name not in PHASE_FLOWS:
                problems.append(f"{key}: step {name} moves {sorted(conserved)} without a flow category")
    assert problems == [], "\n".join(problems)


def row_class_names() -> dict[str, str]:
    return {mapper.local_table.name: mapper.class_.__name__ for mapper in Base.registry.mappers if mapper.local_table is not None}


def fixup_files() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in BACKEND.rglob("*.py"):
        if "alembic" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for key in re.findall(r'_FIXUP = "([a-z0-9_.]+)"', text):
            found[key] = text
    return found


def table_backfilled(table: str, text: str, classes: dict[str, str], fixups: dict[str, str]) -> bool:
    head = text.split(":", 1)[0].strip()
    if head in PLAIN_BACKFILLS:
        return True
    if head in PHASE_REGISTRY:
        return f"table.{table}" in declared_writes(PHASE_REGISTRY[head].run)
    if head in fixups:
        return table in fixups[head] or classes.get(table, table) in fixups[head]
    revision = head.removeprefix("migration ").strip()
    return any(table in path.read_text(encoding="utf-8") for path in VERSIONS.glob(f"{revision}_*.py"))


def test_every_table_a_mechanic_owns_has_its_own_backfill_rule() -> None:
    classes = row_class_names()
    fixups = fixup_files()
    problems: list[str] = []
    for key, mechanic in REGISTERED.items():
        for table in mechanic.tables:
            text = table_backfill(key, mechanic, table)
            if not backfill_known(text) or not table_backfilled(table, text, classes, fixups):
                problems.append(f"{key}: table {table} has no backfill rule of its own ({text[:50]})")
    assert problems == [], "\n".join(problems)


def test_per_table_backfill_overrides_name_real_mechanic_tables() -> None:
    stale = [pair for pair in TABLE_BACKFILLS if pair[0] not in REGISTERED or pair[1] not in REGISTERED[pair[0]].tables]
    assert stale == []


def test_the_compliance_catalogue_resolves_to_real_code() -> None:
    source = backend_source()
    frontend = frontend_source()
    tables = set(Base.metadata.tables)
    prompts = {item.value for item in PromptId}
    tools = {item.value for item in SonToolId} | {item.value for item in MortalToolId}
    problems: list[str] = []
    for row in CATALOGUE:
        problems.extend(f"{row.section}: unknown table {table}" for table in row.tables if table not in tables)
        problems.extend(f"{row.section}: unknown step {phase}" for phase in row.phases if phase not in PHASE_REGISTRY)
        problems.extend(f"{row.section}: missing lever {lever}" for lever in row.levers if lever not in ACTIONS_BY_ID)
        problems.extend(f"{row.section}: surface {surface} is not rendered" for surface in row.surfaces if surface not in frontend)
        problems.extend(f"{row.section}: unknown context {context}" for context in row.contexts if context not in prompts)
        problems.extend(f"{row.section}: unknown tool {tool}" for tool in row.tools if tool not in tools)
        problems.extend(f"{row.section}: no template starts with {prefix}" for prefix in row.templates if not template_written(prefix, source))
        problems.extend(
            f"{row.section}: backfill {item} is not in the code" for item in row.backfill if item not in source and not any(VERSIONS.glob(f"{item}_*.py"))
        )
    assert problems == [], "\n".join(problems)
