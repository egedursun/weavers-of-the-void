from aerona.domain.enums.entity import EntityType
from aerona.services.books.model import ENCYCLOPEDIA_ORDER, OWN_SECTIONS


def test_every_kind_of_record_has_a_place_in_the_encyclopedia_or_a_section_of_its_own() -> None:
    placed = set(ENCYCLOPEDIA_ORDER) | OWN_SECTIONS
    assert [kind.value for kind in EntityType if kind not in placed] == []
    assert len(ENCYCLOPEDIA_ORDER) == len(set(ENCYCLOPEDIA_ORDER))
