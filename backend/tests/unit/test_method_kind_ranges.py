import re

from sqlalchemy import CheckConstraint

from aerona.catalog.methods import METHODS
from aerona.db.tables.nature_kinds import ProductionMethodKindRow

BOUNDS = re.compile(r"(\w+) BETWEEN (-?\d+) AND (-?\d+)")


def bounds() -> dict[str, tuple[int, int]]:
    found: dict[str, tuple[int, int]] = {}
    for constraint in ProductionMethodKindRow.__table__.constraints:
        if isinstance(constraint, CheckConstraint):
            for column, low, high in BOUNDS.findall(str(constraint.sqltext)):
                found[column] = (int(low), int(high))
    return found


def test_every_built_in_method_fits_the_ranges_its_kind_row_allows() -> None:
    limits = bounds()
    assert {"output_pct", "labour_pct", "quality_bonus", "energy_need"} <= set(limits)
    outside = [
        f"{kind.value}.{column}"
        for kind, spec in METHODS.items()
        for column, (low, high) in limits.items()
        if hasattr(spec, column) and not low <= getattr(spec, column) <= high
    ]
    assert outside == []
