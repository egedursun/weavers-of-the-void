from aerona.domain.models.records import EpochStatsData
from aerona.services.statistics import numeric_deltas


def test_a_count_kept_only_from_a_later_epoch_has_no_change_until_both_are_known() -> None:
    before = EpochStatsData(population=100)
    after = EpochStatsData(population=120, soldiers=300, travelling=None)
    deltas = numeric_deltas(after, before)
    assert deltas["population"] == 20
    assert "soldiers" not in deltas
    assert "travelling" not in deltas
    assert numeric_deltas(EpochStatsData(soldiers=310), after)["soldiers"] == 10


def test_an_old_epoch_reads_back_without_the_new_counts() -> None:
    stored = EpochStatsData.model_validate({"population": 5})
    assert (stored.soldiers, stored.travelling) == (None, None)
