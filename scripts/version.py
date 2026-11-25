import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYTHON_PROJECTS = (ROOT / "backend", ROOT / "image-worker")
FRONTEND = ROOT / "frontend"
VERSION_TEXT = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+?)?"


@dataclass(frozen=True)
class Mention:
    path: Path
    pattern: re.Pattern[str]
    escaped: bool = False

    def read(self) -> str:
        found = self.pattern.search(self.path.read_text(encoding="utf-8"))
        if found is None:
            return ""
        return found[2].replace("--", "-") if self.escaped else found[2]

    def write(self, value: str) -> None:
        shown = value.replace("-", "--") if self.escaped else value
        text = self.path.read_text(encoding="utf-8")
        self.path.write_text(
            self.pattern.sub(lambda found: f"{found[1]}{shown}{found[3]}", text),
            encoding="utf-8",
        )


MENTIONS = (
    Mention(
        ROOT / "README.md",
        re.compile(r"(badge/version-)((?:[0-9A-Za-z.]|--)+?)(-[0-9a-f]{6}\?style)"),
        escaped=True,
    ),
    Mention(
        ROOT / "docs" / "wov-basic-information.md",
        re.compile(rf"(S\u00fcr\u00fcm )({VERSION_TEXT})(, )"),
    ),
)
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
PARTS = ("major", "minor", "patch")
USAGE = "usage: version.py show | check | set <version> | bump major|minor|patch [<pre-release>] | pre <pre-release> | release"


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    pre: str = ""

    def __str__(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        return f"{core}-{self.pre}" if self.pre else core


def parsed(value: str) -> Version | None:
    found = SEMVER.match(value.strip())
    if found is None:
        return None
    return Version(int(found[1]), int(found[2]), int(found[3]), found[4] or "")


def canonical_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def declared_versions() -> dict[str, str]:
    found = {
        str(project.relative_to(ROOT) / "pyproject.toml"): tomllib.loads(
            (project / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
        for project in PYTHON_PROJECTS
    }
    found["frontend/package.json"] = json.loads(
        (FRONTEND / "package.json").read_text(encoding="utf-8")
    )["version"]
    for mention in MENTIONS:
        found[str(mention.path.relative_to(ROOT))] = mention.read()
    return found


def check() -> int:
    expected = canonical_version()
    if parsed(expected) is None:
        print(
            f"VERSION holds {expected!r}, which is not a version like 0.1.0 or 0.2.0-beta.1"
        )
        return 1
    drifted = {
        path: value for path, value in declared_versions().items() if value != expected
    }
    for path, value in drifted.items():
        print(f"{path}: version {value or 'missing'} does not match VERSION {expected}")
    print(f"version {expected}: {len(drifted)} drift(s)")
    return 1 if drifted else 0


def apply(value: str) -> int:
    if parsed(value) is None:
        print(f"not a version: {value}")
        return 2
    VERSION_FILE.write_text(f"{value}\n", encoding="utf-8")
    for project in PYTHON_PROJECTS:
        subprocess.run(
            ["uv", "version", value, "--no-sync"],
            cwd=project,
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["npm", "version", value, "--no-git-tag-version", "--allow-same-version"],
        cwd=FRONTEND,
        check=True,
        capture_output=True,
    )
    for mention in MENTIONS:
        mention.write(value)
    return check()


def bumped(current: Version, part: str, pre: str = "") -> Version:
    if part == "major":
        return Version(current.major + 1, 0, 0, pre)
    if part == "minor":
        return Version(current.major, current.minor + 1, 0, pre)
    return Version(current.major, current.minor, current.patch + 1, pre)


def current() -> Version:
    found = parsed(canonical_version())
    if found is None:
        raise SystemExit(
            f"VERSION holds {canonical_version()!r}, which is not a version"
        )
    return found


def main(argv: list[str]) -> int:
    match argv:
        case ["show"]:
            print(canonical_version())
            return 0
        case ["check"]:
            return check()
        case ["set", value]:
            return apply(value.removeprefix("v"))
        case ["bump", part] if part in PARTS:
            return apply(str(bumped(current(), part)))
        case ["bump", part, pre] if part in PARTS:
            return apply(str(bumped(current(), part, pre)))
        case ["pre", pre]:
            now = current()
            return apply(str(Version(now.major, now.minor, now.patch, pre)))
        case ["release"]:
            now = current()
            return apply(str(Version(now.major, now.minor, now.patch)))
        case _:
            print(USAGE)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
