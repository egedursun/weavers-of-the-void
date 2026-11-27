from aerona.domain.models.moment import Moment


def test_a_moment_lifted_to_a_floor_known_only_by_its_year_keeps_its_time_of_year() -> None:
    assert Moment(381, 2, 40, 3).at_least(Moment(386)) == Moment(386, 2, 40, 3)
    assert Moment(381, 2, 40, 3).at_least(Moment(386, 1, 5, 1)) == Moment(386, 1, 5, 1)
    assert Moment(390, 2, 40, 3).at_least(Moment(386)) == Moment(390, 2, 40, 3)
    assert Moment(390, 2).at_least(None) == Moment(390, 2)
