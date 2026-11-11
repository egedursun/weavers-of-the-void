import typing
from enum import Enum

from sqlalchemy import JSON

from aerona.db.base import Base


def enum_inside(annotation: object) -> bool:
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return True
    return any(enum_inside(argument) for argument in typing.get_args(annotation))


def test_a_json_column_never_claims_to_hold_enums() -> None:
    lying = []
    for mapper in Base.registry.mappers:
        hints = typing.get_type_hints(mapper.class_)
        for column in mapper.local_table.columns:
            if isinstance(column.type, JSON) and column.key in hints and enum_inside(typing.get_args(hints[column.key])):
                lying.append(f"{mapper.local_table.name}.{column.key}")
    assert lying == []
