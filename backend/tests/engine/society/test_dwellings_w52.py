from aerona.catalog.genetics import DWELLINGS, dwelling_spec
from aerona.domain.enums.genetics import DwellingKind
from aerona.domain.enums.intervention import Disaster
from aerona.rules.registry import Rules

RULES = Rules()


def test_fifteen_dwellings_and_what_shelters() -> None:
    assert len(DWELLINGS) == len(DwellingKind) == 15
    stilts = DWELLINGS[DwellingKind.STILT_HOUSE]
    assert stilts.floods is not None and stilts.floods(RULES) == RULES.dwellings.stilt_flood_cut_pct
    burrow = DWELLINGS[DwellingKind.BURROW]
    assert burrow.cold is not None and burrow.cold(RULES) == RULES.dwellings.burrow_cold_cut_pct
    assert dwelling_spec("farmstead") is DWELLINGS[DwellingKind.FARMSTEAD]
    assert dwelling_spec("not a dwelling") is None and dwelling_spec(None) is None
    assert {kind for kind, spec in DWELLINGS.items() if spec.since_w52} == {
        DwellingKind.FARMSTEAD,
        DwellingKind.STILT_HOUSE,
        DwellingKind.BURROW,
        DwellingKind.NEST,
        DwellingKind.SUBMERGED,
    }
    assert Disaster.FLOOD in Disaster
