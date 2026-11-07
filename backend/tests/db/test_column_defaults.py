from typing import Any

from sqlalchemy import ColumnDefault

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.tables.finance import CreditProfileRow


def test_a_new_credit_row_counts_its_first_default_before_it_is_flushed() -> None:
    row = CreditProfileRow(subject_node_id=1, rating=50)
    row.defaults += 1
    assert row.defaults == 1


def test_every_mapped_row_carries_its_column_defaults_from_construction() -> None:
    missing: list[str] = []
    assert tables.__all__
    for mapper in Base.registry.mappers:
        kind: Any = mapper.class_
        if mapper.polymorphic_identity is None and mapper.polymorphic_on is not None:
            continue
        row = kind()
        for attribute in mapper.column_attrs:
            column = attribute.columns[0]
            default = column.default
            if isinstance(default, ColumnDefault) and default.is_scalar and not column.primary_key and getattr(row, attribute.key) != default.arg:
                missing.append(f"{mapper.class_.__name__}.{attribute.key}")
    assert missing == []
