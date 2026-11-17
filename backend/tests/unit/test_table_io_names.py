from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import aliased

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.engine.interconnect.table_io import table_names


def test_an_aliased_table_is_recorded_by_its_own_name() -> None:
    other = aliased(EntityRow)
    froms = select(other.id).get_final_froms()
    assert {name for item in froms for name in table_names(item)} == {"entities", "nodes"}


def test_both_sides_of_a_join_are_recorded() -> None:
    froms = select(EntityRow.id).join(NodeRow, NodeRow.id == EntityRow.id).get_final_froms()
    names = {name for item in froms for name in table_names(item)}
    assert {"entities", "nodes"} <= names
    assert not any("anon" in name or "%(" in name for name in names)


def test_no_engine_step_declares_an_anonymous_table() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"
    found = [str(path.relative_to(source)) for path in sorted(source.rglob("*.py")) if "anon)s" in path.read_text(encoding="utf-8")]
    assert found == []
