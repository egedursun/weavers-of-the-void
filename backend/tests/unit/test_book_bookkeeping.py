from sqlalchemy.orm import Mapper

from aerona.constants.control import BOOKKEEPING_TABLES
from aerona.db.base import Base
from aerona.db.profile_guard import table_name
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.services.books.typed import TypedIndex


def mappers_of(tables: frozenset[str]) -> list[Mapper[object]]:
    return [mapper for mapper in Base.registry.mappers if table_name(mapper) in tables]


def test_no_bookkeeping_table_reaches_the_records_of_the_cosmos() -> None:
    index = TypedIndex({})
    for mapper in mappers_of(BOOKKEEPING_TABLES):
        index.add_records(mapper, [AppliedFixupRow(key="kept.out", result={"rows": 1})] if mapper.class_ is AppliedFixupRow else [])
    assert index.records == []
    assert {table_name(mapper) for mapper in mappers_of(BOOKKEEPING_TABLES)} == set(BOOKKEEPING_TABLES)
