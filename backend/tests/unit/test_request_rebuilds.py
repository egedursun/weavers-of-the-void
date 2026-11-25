import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3] / "frontend" / "src"
REBUILD = re.compile(r"new Request\(\s*([^,()]+(?:\([^()]*\))?)\s*,\s*(\{|init\b|[^\s])", re.S)
REQUEST_INPUT = re.compile(r"^(request|original|\w*Request)$")


def rebuilds(text: str) -> list[str]:
    found = []
    for match in REBUILD.finditer(text):
        source, init = match.group(1).strip(), match.group(2)
        if init not in ("{", "init") or REQUEST_INPUT.match(source):
            found.append(match.group(0))
    return found


def test_no_request_is_rebuilt_over_another_request() -> None:
    problems = [
        f"{path.relative_to(SOURCE)}: {found}"
        for path in sorted(SOURCE.rglob("*.ts*"))
        if ".test." not in path.name
        for found in rebuilds(path.read_text(encoding="utf-8"))
    ]
    assert problems == []


def test_the_rule_catches_a_rebuild_that_streams_the_body() -> None:
    assert rebuilds("const next = new Request(url, request)") != []
    assert rebuilds("new Request(request, { body: text })") != []
    assert rebuilds("new Request(url, { method: request.method, body })") == []
    assert rebuilds("new Request(input as RequestInfo, init)") == []
