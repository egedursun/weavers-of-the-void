import pytest

from aerona.db.tables.environment import WorldSeasonRow
from aerona.domain.enums.culture import TraditionKind
from aerona.engine.lore.calendar_rites import SEASON_OF, preferred_season

K = TraditionKind


def season(position: int, *, heat: int = 0, growth: int = 0, travel: int = 0, campaign: int = 0) -> WorldSeasonRow:
    return WorldSeasonRow(
        world_id=1, position=position, name=f"Season {position}", temperature_shift=heat, rain_shift=0, growth=growth, travel=travel, campaign=campaign
    )


YEAR = [
    season(0, heat=-20, growth=10, travel=30, campaign=10),
    season(1, heat=5, growth=80, travel=50, campaign=40),
    season(2, heat=30, growth=40, travel=90, campaign=95),
    season(3, heat=-5, growth=5, travel=20, campaign=20),
]


@pytest.mark.parametrize(
    ("kind", "position"),
    [
        (K.FESTIVAL, 1),
        (K.HARVEST_RITE, 1),
        (K.OFFERING, 1),
        (K.FAST, 3),
        (K.MOURNING, 3),
        (K.ANCESTOR_FEAST, 0),
        (K.NIGHT_VIGIL, 0),
        (K.SIESTA, 2),
        (K.WAR_DANCE, 2),
        (K.INITIATION, 2),
        (K.PILGRIMAGE, 2),
    ],
)
def test_each_rite_keeps_the_season_that_suits_it(kind: TraditionKind, position: int) -> None:
    assert preferred_season(kind, YEAR) == position


def test_ties_go_to_the_earliest_season_and_a_rite_without_a_season_keeps_none() -> None:
    flat = [season(0, campaign=50, travel=50), season(1, campaign=50, travel=50)]
    assert preferred_season(K.WAR_DANCE, flat) == 0
    assert preferred_season(K.PILGRIMAGE, flat) == 0
    unseasoned = next(kind for kind in TraditionKind if kind not in SEASON_OF)
    assert preferred_season(unseasoned, YEAR) is None
    assert preferred_season(K.FESTIVAL, YEAR[:1]) is None
