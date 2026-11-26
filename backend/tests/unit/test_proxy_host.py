import re
from pathlib import Path

import pytest
from starlette.datastructures import Headers

from aerona.api.security import OriginGuard, RefusalError

ROOT = Path(__file__).resolve().parents[3]
NGINX = ROOT / "deploy" / "nginx.conf"
HOST_HEADER = re.compile(r"proxy_set_header\s+Host\s+(\S+);")
PAGE_HOST = "127.0.0.1:8096"
PAGE_ORIGIN = f"http://{PAGE_HOST}"
NGINX_HOST_VALUES = {"$http_host": PAGE_HOST, "$host": "127.0.0.1"}


def forwarded_hosts() -> list[str]:
    found = HOST_HEADER.findall(NGINX.read_text(encoding="utf-8"))
    assert found, "deploy/nginx.conf forwards no Host header to the backend"
    return found


async def passthrough(scope: object, receive: object, send: object) -> None:
    return None


def guard() -> OriginGuard:
    return OriginGuard(passthrough, allowed_origins=[], limits=[])


@pytest.mark.parametrize("variable", forwarded_hosts())
def test_proxy_forwards_the_host_with_its_port(variable: str) -> None:
    assert variable in NGINX_HOST_VALUES, f"unknown Host value {variable} in deploy/nginx.conf"
    headers = Headers(
        {
            "host": NGINX_HOST_VALUES[variable],
            "origin": PAGE_ORIGIN,
            "sec-fetch-site": "same-origin",
            "content-type": "application/json",
        }
    )
    try:
        guard().check(headers, "POST", "/api/auth/setup")
    except RefusalError as refusal:
        pytest.fail(f"a write from the app's own page on {PAGE_HOST} is refused behind nginx: {refusal.message}")


def test_a_host_without_its_port_is_refused() -> None:
    headers = Headers(
        {
            "host": NGINX_HOST_VALUES["$host"],
            "origin": PAGE_ORIGIN,
            "sec-fetch-site": "same-origin",
            "content-type": "application/json",
        }
    )
    with pytest.raises(RefusalError):
        guard().check(headers, "POST", "/api/auth/setup")
