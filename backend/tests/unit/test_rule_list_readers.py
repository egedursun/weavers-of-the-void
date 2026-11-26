import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src"
RULE_EDITOR = FRONTEND / "features" / "world-rules" / "api.ts"
FULL_LIST_READ = re.compile(r"GET\(\s*['\"`]/api/rules['\"`]")


def is_app_source(path: Path) -> bool:
    return ".test." not in path.name and "generated" not in path.parts and "test-utils" not in path.parts


def full_list_readers(root: Path) -> list[str]:
    readers = (path for path in root.rglob("*.ts*") if is_app_source(path) and FULL_LIST_READ.search(path.read_text(encoding="utf-8")))
    return sorted(str(path.relative_to(root)) for path in readers)


def test_only_the_rule_editor_downloads_the_whole_rule_catalogue() -> None:
    assert full_list_readers(FRONTEND) == [str(RULE_EDITOR.relative_to(FRONTEND))]


def test_a_screen_reading_the_whole_catalogue_is_caught(tmp_path: Path) -> None:
    (tmp_path / "ok.ts").write_text("api.GET('/api/rules/values')\n", encoding="utf-8")
    (tmp_path / "bad.tsx").write_text("unwrap(api.GET('/api/rules'))\n", encoding="utf-8")
    assert full_list_readers(tmp_path) == ["bad.tsx"]
