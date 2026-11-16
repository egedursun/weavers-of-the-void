from aerona.catalog.law_areas import LAW_AREAS
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import LawArea, LawKind
from aerona.engine.polity.law_areas import AREA_LOBBIES, area_order, pressed
from aerona.rules.registry import Rules


def test_every_law_has_an_area_and_every_area_has_lobbies() -> None:
    assert set(LAW_AREAS) == set(LawKind)
    assert all(AREA_LOBBIES[area] for area in LawArea)


def test_penal_laws_lean_on_order_more_than_constitutions() -> None:
    assert area_order(LawArea.PENAL) > area_order(LawArea.CONSTITUTIONAL)


def test_only_factions_of_an_area_press_on_its_laws() -> None:
    lobbies = {FactionKind.CRIME_FAMILY: 80, FactionKind.MERCHANT_GUILD: 60}
    assert pressed(Rules(), LawArea.PENAL, lobbies) > 0
    assert pressed(Rules(), LawArea.MILITARY, lobbies) == 0
