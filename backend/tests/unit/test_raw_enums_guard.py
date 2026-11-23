import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"
GUARD = FRONTEND / "scripts" / "check_raw_enums.mjs"

SEASON = "type Season = 'long_winter' | 'short_summer'\n"

SPACED_BY_HAND = (
    SEASON
    + """
export function SeasonName({ season }: { season: Season }) {
  return <span>{season.replaceAll('_', ' ')}</span>
}
"""
)

SPACED_BY_PATTERN = (
    SEASON
    + """
export function SeasonTitle({ season }: { season: Season }) {
  return <span title={season.replace(/_/g, ' ')}>Season</span>
}
"""
)

SPACED_THROUGH_HELPER = (
    SEASON
    + """
function spaced(value: string): string {
  const text = value.replace(/[_:]+/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function SeasonCaption({ season }: { season: Season }) {
  return <span>{`Comes as ${spaced(season)}`}</span>
}
"""
)

SHOWN_THROUGH_LABELS = (
    SEASON
    + """
const SEASONS: Record<Season, string> = { long_winter: 'Long winter', short_summer: 'Short summer' }

function labelled(value: string, table: Record<string, string>): string {
  return table[value] ?? value.replaceAll('_', ' ')
}

export function SeasonName({ season }: { season: Season }) {
  return (
    <span data-key={season.replaceAll('_', '-')} title={labelled(season, SEASONS)}>
      {SEASONS[season]}
    </span>
  )
}
"""
)


def guard(folder: Path, sources: dict[str, str]) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is needed to run the frontend guards")
    folder.mkdir()
    for name, source in sources.items():
        (folder / name).write_text(source)
    return subprocess.run([node, str(GUARD), str(folder)], cwd=FRONTEND, capture_output=True, text=True, check=False)


def test_an_enum_worded_by_hand_is_caught_directly_and_through_a_helper(tmp_path: Path) -> None:
    run = guard(
        tmp_path / "worded",
        {"SeasonName.tsx": SPACED_BY_HAND, "SeasonTitle.tsx": SPACED_BY_PATTERN, "SeasonCaption.tsx": SPACED_THROUGH_HELPER},
    )
    assert run.returncode == 1
    assert "SeasonName.tsx:4 words season by hand" in run.stdout
    assert "SeasonTitle.tsx:4 words season by hand" in run.stdout
    assert "SeasonCaption.tsx:9 words season by hand through spaced" in run.stdout


def test_an_enum_shown_through_its_label_map_passes(tmp_path: Path) -> None:
    run = guard(tmp_path / "labelled", {"SeasonName.tsx": SHOWN_THROUGH_LABELS})
    assert run.returncode == 0, run.stdout
