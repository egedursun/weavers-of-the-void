from pathlib import Path

from aerona.constants.media import MediaBackend
from aerona.domain.enums.entity import LegendCategory
from aerona.domain.enums.travel import JourneyEventKind
from aerona.migration.legacy.cli import options_from, parser
from aerona.migration.legacy.patterns import LegacyPatterns
from aerona.migration.legacy.vocabulary import load_vocabulary

PATTERNS = LegacyPatterns(load_vocabulary())


def test_old_words_sort_temples_legends_and_journey_events() -> None:
    assert PATTERNS.is_temple("B\u00fcy\u00fck Tap\u0131nak") and not PATTERNS.is_temple("Liman")
    assert PATTERNS.legend_category("Ya\u015fl\u0131 Ejder") is LegendCategory.CREATURE
    assert PATTERNS.legend_category("F\u0131s\u0131lt\u0131 Vadisi") is LegendCategory.SPIRIT
    assert PATTERNS.legend_category("Ye\u015fil Ova") is LegendCategory.RELIC
    assert PATTERNS.legend_category("") is None
    assert PATTERNS.journey_event("korsanlar sald\u0131rd\u0131") is JourneyEventKind.PIRATES
    assert PATTERNS.journey_event("b\u00fcy\u00fck f\u0131rt\u0131na") is JourneyEventKind.VOID_STORM
    assert PATTERNS.journey_event("sakin bir g\u00fcn") is JourneyEventKind.OTHER


def test_the_migration_command_reads_its_options_and_places_media_beside_the_target(tmp_path: Path) -> None:
    arguments = parser().parse_args(["--legacy", str(tmp_path / "old"), "--target", str(tmp_path / "new" / "aerona.db"), "--dry-run"])
    options = options_from(arguments)
    assert options.dry_run and not options.replace and options.media_backend is MediaBackend.FILE
    assert options.media_dir is not None and options.media_dir.parent == (tmp_path / "new").resolve()
    assert options.report_dir is None
    reported = options_from(parser().parse_args(["--legacy", "a", "--target", "b.db", "--report-dir", str(tmp_path / "reports"), "--replace"]))
    assert reported.replace and reported.report_dir == (tmp_path / "reports").resolve()
