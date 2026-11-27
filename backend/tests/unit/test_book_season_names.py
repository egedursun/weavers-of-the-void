from types import SimpleNamespace

from aerona.catalog.season_positions import SEASON_POSITIONS
from aerona.db.base import Base
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.node import NodeBirthRow
from aerona.domain.enums.environment import SeasonDating, WorldLink
from aerona.services.books.typed import SEASON_COLUMNS, TypedIndex

WORLD = 1
NODE = 5


def index_with_seasons() -> TypedIndex:
    index = TypedIndex({})
    index.seasons[WORLD] = {0: "Thaw", 1: "Deep Cold"}
    index.worlds_of = {NODE: WORLD}
    return index


def test_a_route_closed_season_reads_as_the_season_of_its_world() -> None:
    row = TradeRouteProfileRow(route_entity_id=NODE, closed_season=1)
    assert index_with_seasons().value(TradeRouteProfileRow.__table__.columns["closed_season"], 1, row) == "Deep Cold"


def test_a_season_beyond_the_world_still_reads_as_a_season() -> None:
    row = TradeRouteProfileRow(route_entity_id=NODE, closed_season=4)
    assert index_with_seasons().value(TradeRouteProfileRow.__table__.columns["closed_season"], 4, row) == "season 5"


def test_every_registered_season_position_reads_as_a_season_name() -> None:
    index = index_with_seasons()
    positions = list(SEASON_POSITIONS)
    assert positions and {(position.table, position.column) for position in positions} == set(SEASON_COLUMNS)
    for position in positions:
        row = SimpleNamespace(**{position.through: WORLD if position.link is WorldLink.WORLD else NODE})
        assert index.value(Base.metadata.tables[position.table].columns[position.column], 0, row) == "Thaw", position


def test_a_moment_day_reads_one_based_like_the_history_lines() -> None:
    row = NodeBirthRow(node_id=NODE, year=311, season=0, day=101, hour=0)
    columns = NodeBirthRow.__table__.columns
    index = index_with_seasons()
    assert index.value(columns["day"], 101, row) == "102"
    assert index.value(columns["season"], 0, row) == "Thaw"
    assert any(position.dating is SeasonDating.DAY for position in SEASON_POSITIONS)
