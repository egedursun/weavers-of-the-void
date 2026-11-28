import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_raw_error_bodies", REPOSITORY_ROOT / "scripts" / "check_raw_error_bodies.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_raw_error_bodies"] = module
    spec.loader.exec_module(module)
    return module


def test_an_error_worded_from_a_raw_body_is_caught() -> None:
    code = (
        "throw new ApiError(await response.text(), response.status)\n"
        "const note = reply.statusText\n"
        "const sent = await request.clone().text()\n"
        "const body = await res.clone().text()\n"
    )
    assert checker().raw_reads(code) == [1, 2, 4]


def test_a_proxy_without_a_down_answer_is_caught() -> None:
    bare = "server {\n    location /api/ {\n        proxy_pass ${AERONA_BACKEND_ORIGIN};\n    }\n}\n"
    found = checker().nginx_problems(bare)
    assert any("location /api/" in problem for problem in found)
    assert any("no @backend_down" in problem for problem in found)
    assert any("names the backend in proxy_pass" in problem for problem in found)
    assert any("no resolver" in problem for problem in found)


def test_a_down_answer_must_be_json_or_the_page() -> None:
    conf = (
        "server {\n    resolver 127.0.0.11;\n    location /api/ {\n        set $b http://b;\n        proxy_pass $b;\n"
        "        error_page 502 504 =503 @backend_down;\n    }\n"
        "    location @backend_down {\n        return 503 'down';\n    }\n}\n"
    )
    assert checker().nginx_problems(conf) == ["@backend_down must answer requests with JSON and browser pages with /backend-down.html"]


def test_the_app_never_shows_a_raw_error_body() -> None:
    assert checker().problems() == []
