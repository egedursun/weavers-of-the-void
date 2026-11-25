import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "deploy"
COPY = re.compile(r"^COPY\s+(?!--from)((?:--\S+\s+)*)(.+)$", re.M)


def pattern_regex(pattern: str) -> re.Pattern[str]:
    parts = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(parts) + "(/.*)?$")


def kept(path: str, rules: list[tuple[bool, re.Pattern[str]]]) -> bool:
    keep = True
    for negated, regex in rules:
        if regex.match(path):
            keep = negated
    return keep


def ignore_rules(dockerfile: Path) -> list[tuple[bool, re.Pattern[str]]]:
    ignore = dockerfile.with_name(dockerfile.name + ".dockerignore")
    rules = []
    for raw in ignore.read_text(encoding="utf-8").splitlines():
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        negated = entry.startswith("!")
        rules.append((negated, pattern_regex(entry.removeprefix("!").removeprefix("/"))))
    return rules


def tracked(source: str) -> list[str]:
    found = subprocess.run(["git", "ls-files", "--", source], cwd=ROOT, capture_output=True, text=True, check=True)
    return found.stdout.split()


def copied_sources(dockerfile: Path) -> list[str]:
    sources = []
    for match in COPY.finditer(dockerfile.read_text(encoding="utf-8")):
        sources.extend(match.group(2).split()[:-1])
    return sources


def test_every_copied_file_reaches_its_build_context() -> None:
    missing = []
    for dockerfile in sorted(DEPLOY.glob("*.Dockerfile")):
        rules = ignore_rules(dockerfile)
        for source in copied_sources(dockerfile):
            files = tracked(source)
            if not files or not any(kept(path, rules) for path in files):
                missing.append(f"{dockerfile.name}: {source}")
    assert missing == []


def test_the_rule_reads_an_ignore_like_docker() -> None:
    rules = [(False, pattern_regex("**")), (True, pattern_regex("backend/src/**"))]
    assert kept("backend/src/aerona/main.py", rules)
    assert not kept("scripts/backup_library.py", rules)
