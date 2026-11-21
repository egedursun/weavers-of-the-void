import ast
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.domain.enums.records import StepAction

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_incident_kinds", REPOSITORY_ROOT / "scripts" / "check_incident_kinds.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_incident_kinds"] = module
    spec.loader.exec_module(module)
    return module


def call_of(source: str) -> ast.Call:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    return node.value


def test_a_name_handed_to_a_number_fact_is_caught() -> None:
    module = guard()
    spec = INCIDENT_KINDS["power.hive_mind"]
    wrong = call_of('record(ctx, "power.hive_mind", roles={}, facts={"people": len(folk)})')
    assert module.shape_problems(spec, wrong) == ["gives the name fact people of power.hive_mind a number"]
    right = call_of('record(ctx, "power.hive_mind", roles={}, facts={"people": people.name})')
    assert module.shape_problems(spec, right) == []


def test_several_nodes_handed_to_a_single_role_are_caught() -> None:
    module = guard()
    spec = INCIDENT_KINDS["tongue.fault_found"]
    single = next(role for role in spec.roles if not role.many)
    name = single.role.name
    wrong = call_of(f'record(ctx, "tongue.fault_found", roles={{IncidentRole.{name}: [one.id for one in folk]}}, facts={{}})')
    assert module.many_problems(spec, wrong) == [f"gives several nodes to the single role {single.role.value} of tongue.fault_found; declare it many"]
    many = replace(spec, roles=tuple(replace(role, many=True) if role is single else role for role in spec.roles))
    assert module.many_problems(many, wrong) == []


def test_a_step_built_for_a_kind_that_does_not_declare_it_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    module = guard()
    arrival = INCIDENT_KINDS["travel.arrival"]
    narrowed = {**module.INCIDENT_KINDS, "travel.arrival": replace(arrival, steps=arrival.steps - {StepAction.OFFER})}
    monkeypatch.setattr(module, "INCIDENT_KINDS", narrowed)
    found = module.step_flow_problems(module.write_sites())
    assert any(line.startswith("engine/cosmos/pilgrimage.py") and "OFFER" in line for line in found)


def test_a_step_a_helper_appends_to_a_kind_that_does_not_declare_it_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    module = guard()
    journey = INCIDENT_KINDS["travel.journey"]
    narrowed = {**module.INCIDENT_KINDS, "travel.journey": replace(journey, steps=journey.steps - {StepAction.FOUND})}
    monkeypatch.setattr(module, "INCIDENT_KINDS", narrowed)
    assert any("FOUND to travel.journey" in line for line in module.helper_step_problems())


def test_a_shipped_kind_that_leaves_the_catalog_needs_a_rename_migration(tmp_path: Path) -> None:
    module = guard()
    assert module.catalog_keys('IncidentKindSpec("travel.route_stitched", G.MOVEMENT, "x")') == {"travel.route_stitched"}
    shipped = {"travel.route_stitched", "travel.arrival"}
    assert module.retired_kind_problems(shipped, {"travel.arrival", "travel.route_reopened"}, set())
    (tmp_path / "rename.py").write_text('RENAMED_KINDS = (("travel.route_stitched", "travel.route_reopened"),)\n', encoding="utf-8")
    renamed = module.renamed_kinds(tmp_path)
    assert renamed == {"travel.route_stitched"}
    assert module.retired_kind_problems(shipped, {"travel.arrival", "travel.route_reopened"}, renamed) == []


def test_every_retired_kind_key_is_renamed_in_stored_records() -> None:
    module = guard()
    renamed = module.renamed_kinds()
    assert {"travel.route_stitched", "tools.son.stitch", "fate.thread_closed", "institutions.place_swallowed"} <= renamed
    assert not renamed & set(INCIDENT_KINDS)
