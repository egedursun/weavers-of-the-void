import re
from pathlib import Path

from aerona.constants.api import IMMUTABLE_CACHE, NO_CACHE, PUBLIC_FILE_CACHE

ROOT = Path(__file__).resolve().parents[3]
NGINX = ROOT / "deploy" / "nginx.conf"
LOCATION = re.compile(r"location\s+([^{]+?)\s*\{([^{}]*)\}")
CACHE_HEADER = re.compile(r'add_header\s+Cache-Control\s+"([^"]+)"')


def caches() -> dict[str, list[str]]:
    return {target: CACHE_HEADER.findall(body) for target, body in LOCATION.findall(NGINX.read_text(encoding="utf-8"))}


def test_the_proxy_caches_static_files_as_the_backend_does() -> None:
    found = caches()
    assert found["/assets/"] == [IMMUTABLE_CACHE]
    assert found["= /index.html"] == [NO_CACHE]
    assert found["/"] == [PUBLIC_FILE_CACHE]


def test_only_the_page_shell_is_revalidated_on_every_load() -> None:
    revalidated = [target for target, headers in caches().items() if NO_CACHE in headers]
    assert revalidated == ["= /index.html"]
