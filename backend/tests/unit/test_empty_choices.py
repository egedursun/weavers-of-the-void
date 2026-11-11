from sqlalchemy.sql.sqltypes import Enum as SqlEnum

from aerona.db import tables
from aerona.db.base import Base
from aerona.engine.primitives.edits import coerce
from aerona.services.player.profiles import coerce as coerce_profile


def none_columns() -> list[tuple[type[Base], str, object]]:
    assert tables.ArmsRow is not None
    found: list[tuple[type[Base], str, object]] = []
    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            kind = column.type
            if isinstance(kind, SqlEnum) and kind.enum_class is not None and not column.nullable and not column.primary_key:
                member = next((item for item in kind.enum_class if str(getattr(item, "value", "")) == "none"), None)
                if member is not None:
                    found.append((mapper.class_, column.key, member))
    return found


def test_an_empty_pick_on_a_required_choice_with_a_none_value_means_none() -> None:
    found = none_columns()
    assert len(found) > 3
    for row_class, key, member in found:
        assert coerce(row_class.__new__(row_class), key, None, {}) is member, (row_class.__name__, key)
        assert coerce_profile(row_class.__mapper__, key, None) is member, (row_class.__name__, key)
