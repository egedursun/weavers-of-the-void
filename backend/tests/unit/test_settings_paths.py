from pathlib import Path

import pytest
from pydantic import ValidationError

from aerona.settings import PATH_FIELDS, Settings

EDGED = ("data ", " data", "worlds/katharis /data", "\tdata")


@pytest.mark.parametrize("field", PATH_FIELDS)
@pytest.mark.parametrize("folder", EDGED)
def test_a_path_setting_with_a_folder_edged_by_a_space_stops_the_server(field: str, folder: str, tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="begins or ends with a space"):
        Settings.model_validate({field: tmp_path / folder})


@pytest.mark.parametrize("field", PATH_FIELDS)
def test_a_plain_path_setting_is_kept_as_given(field: str, tmp_path: Path) -> None:
    folder = tmp_path / "test data" / "divine-will-2026-11-25"
    assert getattr(Settings.model_validate({field: folder}), field) == folder


def test_the_data_dir_from_the_environment_is_checked_too(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AERONA_DATA_DIR", f"{tmp_path}/divine-will-2026-11-25 ")
    with pytest.raises(ValidationError, match="data_dir names a folder"):
        Settings(_env_file=None)
