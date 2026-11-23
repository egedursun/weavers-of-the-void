from types import SimpleNamespace

from aerona.catalog.season_positions import SEASON_POSITIONS
from aerona.db.base import Base
from aerona.db.tables.economy import TradeRouteProfileRow
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
    positions = [position for position in SEASON_POSITIONS if position.dating is SeasonDating.POSITION]
    assert positions and {(position.table, position.column) for position in positions} == set(SEASON_COLUMNS)
    for position in positions:
        row = SimpleNamespace(**{position.through: WORLD if position.link is WorldLink.WORLD else NODE})
        assert index.value(Base.metadata.tables[position.table].columns[position.column], 0, row) == "Thaw", position
