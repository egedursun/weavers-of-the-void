import re

from sqlalchemy import Integer

from aerona.db.base import Base
from aerona.db.tables.climes import RegionWindRow
from aerona.db.tables.operations import ShipStateRow
from aerona.services.books.typed import NAMED_NUMBERS, TypedIndex

COMPASS_COLUMN = re.compile(r"(?:^|_)(?:heading|wind_from|direction|octant|bearing|facing)(?:_|$)")


def test_a_wind_and_a_heading_read_as_compass_points_in_the_book() -> None:
    index = TypedIndex({})
    assert index.value(RegionWindRow.__table__.columns["wind_from"], 2) == "east"
    assert index.value(ShipStateRow.__table__.columns["heading"], 6) == "west"
    assert index.value(ShipStateRow.__table__.columns["wind_from"], 0) == "north"


def test_every_compass_column_is_named_in_the_book() -> None:
    unnamed = sorted(
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, Integer) and COMPASS_COLUMN.search(column.name) and column.name not in NAMED_NUMBERS
    )
    assert unnamed == []
