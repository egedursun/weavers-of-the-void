from sqlalchemy import Enum as SqlEnum

from aerona.core.grammar import fact_word
from aerona.db.base import Base
from aerona.db.tables.body import InjuryRow
from aerona.services.books.records import enum_of


def test_a_changed_enum_value_is_told_in_words_for_every_enum_column() -> None:
    raw = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, SqlEnum)
        and column.type.enum_class is not None
        and any("_" in fact_word(enum_of(table.name, column.name), str(member.value)) for member in column.type.enum_class)
    ]
    assert raw == []
    assert fact_word(enum_of(InjuryRow.__tablename__, "state"), "healed_scar") == "healed scar"
