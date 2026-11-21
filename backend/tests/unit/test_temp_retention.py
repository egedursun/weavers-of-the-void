import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_a_passing_test_leaves_no_temporary_files_behind_so_a_full_run_cannot_fill_the_disk() -> None:
    options = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert options["tmp_path_retention_policy"] == "failed"
