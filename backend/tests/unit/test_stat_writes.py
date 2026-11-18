import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.primitives.stats import set_stats

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def test_a_stat_out_of_its_range_is_refused_where_it_is_written_not_where_it_is_read() -> None:
    town = EntityRow(
        name="Ardun",
        entity_type=EntityType.SETTLEMENT,
        description="",
        stats=SettlementStats(wealth=10),
        power_level=1,
        origin=EntityOrigin.ENGINE,
        birth_epoch=1,
        status=EntityStatus.CANON,
    )
    with pytest.raises(ValidationError):
        set_stats(town, wealth=300)


def test_no_code_copies_stats_without_validating_them() -> None:
    found = []
    for path in sorted(SOURCE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "model_copy"
                and "stats" in ast.unparse(node.func.value).split(".")[-1]
                and any(keyword.arg == "update" for keyword in node.keywords)
            ):
                found.append(f"{path.relative_to(SOURCE)}:{node.lineno}")
    assert found == [], f"model_copy(update=...) skips validation; use revised() from domain.models.entity_stats: {found}"
