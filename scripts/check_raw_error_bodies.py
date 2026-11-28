import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "frontend" / "src"
ERRORS_MODULE = SOURCE_ROOT / "api" / "errors.ts"
NGINX_CONF = ROOT / "deploy" / "nginx.conf"
DOWN_PAGE = ROOT / "frontend" / "public" / "backend-down.html"
DOWN_LOCATION = "@backend_down"
RAW_READS = (
    re.compile(r"\bnew ApiError\("),
    re.compile(r"\.statusText\b"),
    re.compile(r"\b(?:response|res|reply|answer|result)\.(?:clone\(\)\.)?text\(\)"),
)
STRING_BODY = re.compile(r"typeof\s+body\s*===\s*['\"]string['\"]")
LOCATION = re.compile(r"location\s+([^{]+)\{")
FALLBACK = re.compile(r"error_page\s+502\s+504\s+=503\s+" + re.escape(DOWN_LOCATION) + r"\s*;")


def sources() -> list[Path]:
    if not SOURCE_ROOT.exists():
        return []
    return sorted(
        path
        for path in SOURCE_ROOT.rglob("*")
        if path.suffix in {".ts", ".tsx"} and path.is_file() and ".test." not in path.name and "generated" not in path.parts
    )


def raw_reads(code: str) -> list[int]:
    return [number for number, line in enumerate(code.splitlines(), start=1) if any(pattern.search(line) for pattern in RAW_READS)]


def blocks(conf: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in LOCATION.finditer(conf):
        depth, end = 1, match.end()
        while depth and end < len(conf):
            depth += {"{": 1, "}": -1}.get(conf[end], 0)
            end += 1
        found.append((match.group(1).strip(), conf[match.end() : end - 1]))
    return found


def nginx_problems(conf: str) -> list[str]:
    unrouted = [name for name, body in blocks(conf) if "proxy_pass" in body and not FALLBACK.search(body)]
    found = [f"location {name} proxies the backend without routing its 502 and 504 to {DOWN_LOCATION}" for name in unrouted]
    down = [body for name, body in blocks(conf) if name == DOWN_LOCATION]
    if not down:
        found.append(f"no {DOWN_LOCATION} location answers while the backend is down")
    elif "default_type application/json" not in down[0] or DOWN_PAGE.name not in down[0]:
        found.append(f"{DOWN_LOCATION} must answer requests with JSON and browser pages with /{DOWN_PAGE.name}")
    return found


def problems() -> list[str]:
    found = [
        f"{path.relative_to(ROOT)}:{line} builds an error from a raw response body; let errorFromResponse in api/errors.ts word it"
        for path in sources()
        if path != ERRORS_MODULE
        for line in raw_reads(path.read_text(encoding="utf-8"))
    ]
    if ERRORS_MODULE.exists() and STRING_BODY.search(ERRORS_MODULE.read_text(encoding="utf-8")):
        found.append(f"{ERRORS_MODULE.relative_to(ROOT)} shows a text body as the error, so a proxy's HTML page reaches the screen")
    if NGINX_CONF.exists():
        found.extend(f"{NGINX_CONF.relative_to(ROOT)}: {problem}" for problem in nginx_problems(NGINX_CONF.read_text(encoding="utf-8")))
    if not DOWN_PAGE.exists():
        found.append(f"{DOWN_PAGE.relative_to(ROOT)} is missing")
    return found


def main() -> int:
    found = problems()
    for problem in found:
        print(problem)
    print(f"raw error bodies: {len(found)} problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
