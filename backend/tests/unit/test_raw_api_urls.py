import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_raw_api_urls", REPOSITORY_ROOT / "scripts" / "check_raw_api_urls.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_raw_api_urls"] = module
    spec.loader.exec_module(module)
    return module


def test_a_hand_built_api_url_is_found_and_typed_paths_pass(tmp_path: Path) -> None:
    schema = tmp_path / "api" / "generated" / "schema.ts"
    schema.parent.mkdir(parents=True)
    schema.write_text(
        "export interface paths {\n  '/api/book': {\n  }\n  '/api/actions/kin:marry': {\n  }\n  '/api/entities/{entity_id}/rite': {\n  }\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "api" / "url.ts").write_text("const LIBRARY = '/api/library/'\n", encoding="utf-8")
    (tmp_path / "Screen.tsx").write_text(
        "const BOOK_URL = '/api/book'\n"
        "const media = `/api/media/${file}`\n"
        "const a = <a href='/api/book'>x</a>\n"
        "const b = apiUrl(`/api/media/${file}`, { w })\n"
        "const c = api.POST('/api/actions/kin:marry', { body })\n"
        "const d = api.POST(`/api/actions/${name}`, { body })\n"
        "type E = Extract<keyof paths, `/api/actions/${string}`>\n"
        "type F = paths[`/api/actions/${Action}`]['post']\n"
        "const g = path.replace('/api/actions/', '')\n"
        "const h = { path: '/api/entities/{entity_id}/rite' }\n"
        "const i = '/api/book?entity_id=1'\n"
        "const j = new EventSource('/api/events')\n"
        "import { api } from '@/api/client'\n"
        "const k = '/api/unknown/route'\n",
        encoding="utf-8",
    )
    (tmp_path / "Screen.test.tsx").write_text("const raw = '/api/media/x.png'\n", encoding="utf-8")
    (tmp_path / "willFixtures.ts").write_text("onApi('GET', '/api/nodes/7/anatomy', {})\n", encoding="utf-8")
    found = checker().findings(tmp_path, schema)
    assert [(item.line, item.literal) for item in found] == [
        (1, "/api/book"),
        (2, "/api/media/${}"),
        (3, "/api/book"),
        (11, "/api/book?entity_id=1"),
        (12, "/api/events"),
        (14, "/api/unknown/route"),
    ]


def test_no_raw_api_url_bypasses_the_helper_in_the_frontend() -> None:
    assert checker().findings() == []
