from pathlib import Path

from aerona.catalog.titles import SEAT_RANKS, TIER_RANKS
from aerona.domain.enums.statecraft import SubjectKind
from aerona.domain.enums.titles import TitleTier

ENGINE = Path(__file__).resolve().parents[2] / "src" / "aerona" / "engine"


def engine_text() -> str:
    return "\n".join(path.read_text() for path in sorted(ENGINE.rglob("*.py")))


def test_every_title_rank_has_an_engine_path_that_raises_it() -> None:
    assert set(TitleTier) == set(TIER_RANKS) | SEAT_RANKS | {TitleTier.LEAGUE}
    assert "found_title(ctx, realm, TitleTier.LEAGUE" in engine_text()


def test_every_subject_kind_is_chosen_by_the_engine() -> None:
    text = engine_text()
    assert [kind for kind in SubjectKind if f"return SubjectKind.{kind.name}" not in text and f"kind=SubjectKind.{kind.name}" not in text] == []
