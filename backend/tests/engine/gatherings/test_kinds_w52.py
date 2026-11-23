from aerona.catalog.gatherings import GATHERING_COLLECTIONS
from aerona.domain.enums.gathering import CollectionKind, GatheringKind


def test_thirty_six_gathering_kinds_with_commemoration_and_muster() -> None:
    assert len(GatheringKind) == 36
    assert GATHERING_COLLECTIONS[GatheringKind.MUSTER] is CollectionKind.WAR
    assert set(GATHERING_COLLECTIONS) == set(GatheringKind)
