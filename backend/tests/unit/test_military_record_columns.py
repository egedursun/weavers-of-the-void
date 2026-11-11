import pytest

from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.military import WarAimKind
from aerona.engine.military.records import CHOICE, FLAG, INTEGER, KINDS, NUMBER, TEXT, WORDS, Column, as_dict, coerce, columns, scalar

GOOD: dict[str, object] = {FLAG: True, INTEGER: 3, NUMBER: 1.5, WORDS: [], TEXT: "plain"}
BAD: dict[str, object] = {FLAG: 1, INTEGER: 1.5, NUMBER: "many", WORDS: "a list"}


def good_value(column: Column) -> object:
    return column.options[0] if column.kind == CHOICE else GOOD[column.kind]


@pytest.mark.parametrize("key", sorted(KINDS))
def test_every_column_of_every_military_record_takes_a_value_of_its_kind(key: str) -> None:
    kind = KINDS[key]
    found = columns(kind)
    assert found
    for column in found:
        value = coerce(kind, column, good_value(column))
        assert scalar(value) is not None or column.kind == TEXT
        if column.kind in BAD:
            with pytest.raises(ValidationFailedError):
                coerce(kind, column, BAD[column.kind])
        if column.kind == CHOICE:
            with pytest.raises(ValidationFailedError):
                coerce(kind, column, "not a choice")
        if not column.nullable and "none" in column.options:
            assert scalar(coerce(kind, column, None)) == "none"
        elif not column.nullable:
            with pytest.raises(ValidationFailedError):
                coerce(kind, column, None)


def test_a_record_reads_back_as_plain_values() -> None:
    kind = KINDS["war_aim"]
    row = kind.model(id=7, war_id=1, side_entity_id=2, kind=WarAimKind.LOOT, params={"amount": 3}, achieved=0, locked=[])
    values = as_dict(kind, row)
    assert values["kind"] == "loot" and values["params"] == {"amount": 3} and values["id"] == 7
