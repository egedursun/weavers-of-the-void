from pathlib import Path

import pytest

from aerona.migration.legacy.vocabulary import Vocabulary, load_vocabulary
from tests.migration.legacy_fixture import LegacyFixture, build_world


@pytest.fixture
def vocabulary() -> Vocabulary:
    return load_vocabulary()


@pytest.fixture
def legacy(tmp_path: Path, vocabulary: Vocabulary) -> LegacyFixture:
    fixture = LegacyFixture(tmp_path / "legacy", vocabulary)
    build_world(fixture)
    return fixture
