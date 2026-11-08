from pathlib import Path

import pytest

from tests import conftest


def test_the_lever_template_is_rebuilt_when_any_engine_source_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "aerona"
    source.mkdir()
    module = source / "phase.py"
    module.write_text("STEP = 1\n", encoding="utf-8")
    monkeypatch.setattr(conftest, "ENGINE_SOURCE", source)
    template = tmp_path / "schema.db"
    before = conftest.template_digest(template)
    module.write_text("STEP = 2\n", encoding="utf-8")
    assert conftest.template_digest(template) != before
