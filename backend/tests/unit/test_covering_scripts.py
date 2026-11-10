import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY_ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_a_folder_named_like_a_frontend_test_is_not_a_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    covering = script("covering_frontend_tests")
    source = tmp_path / "src"
    feature = source / "features" / "thing"
    (feature / "__screenshots__" / "thing.test.tsx").mkdir(parents=True)
    (feature / "Thing.tsx").write_text("export const thing = 1\n", encoding="utf-8")
    (feature / "thing.test.tsx").write_text("import { thing } from './Thing'\n", encoding="utf-8")
    monkeypatch.setattr(covering, "SOURCE", source)
    monkeypatch.setattr(covering, "GENERATED", source / "api" / "generated")
    found = covering.covering([feature / "Thing.tsx"])
    assert found == [(feature / "thing.test.tsx").resolve()]


def test_a_folder_named_like_a_backend_test_is_not_a_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    covering = script("covering_tests")
    tests = tmp_path / "tests"
    (tests / "test_folder.py").mkdir(parents=True)
    (tests / "test_real.py").write_text("from aerona.thing import made\n", encoding="utf-8")
    monkeypatch.setattr(covering, "TESTS", tests)
    assert covering.covering({"aerona.thing": {"made"}}) == {tests / "test_real.py"}


def test_a_changed_data_file_reaches_the_tests_of_the_modules_that_read_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    covering = script("covering_tests")
    source = tmp_path / "src"
    package = source / "aerona"
    package.mkdir(parents=True)
    (package / "table.json").write_text("{}", encoding="utf-8")
    (package / "loader.py").write_text('NAME = "table.json"\n', encoding="utf-8")
    (package / "other.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(covering, "SOURCE", source)
    assert covering.readers_of(package / "table.json") == {"aerona.loader": {covering.WHOLE_MODULE}}
