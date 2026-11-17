import pytest

from aerona.catalog.lore import ART_WORDS
from aerona.catalog.techniques import TECHNIQUES
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import ArtMode, Technique
from aerona.engine.lore.civics import unlearned
from aerona.engine.lore.typed_backfill import legacy_medium


def test_an_unlearned_technique_reads_by_its_own_label() -> None:
    assert unlearned(None) == ""
    for technique in Technique:
        assert unlearned(technique) == TECHNIQUES[technique].label.lower()


@pytest.mark.parametrize("medium", list(ART_WORDS))
def test_an_old_artwork_is_typed_by_the_words_of_its_name(medium: ArtMode) -> None:
    word = ART_WORDS[medium][0]
    found = legacy_medium(EntityRow(name=f"The Great {word.title()}", subtype=None))
    assert found is not None and word in ART_WORDS[found]


def test_an_artwork_whose_name_names_no_medium_stays_untyped() -> None:
    assert legacy_medium(EntityRow(name="Qzx", subtype=None)) is None
