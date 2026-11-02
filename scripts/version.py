import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYTHON_PROJECTS = (ROOT / "backend", ROOT / "image-worker")
FRONTEND = ROOT / "frontend"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+.][0-9A-Za-z.-]+)?$")


def canonical_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def declared_versions() -> dict[str, str]:
    found = {
        str(project.relative_to(ROOT) / "pyproject.toml"): tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        for project in PYTHON_PROJECTS
    }
    found["frontend/package.json"] = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))["version"]
    return found


def check() -> int:
    expected = canonical_version()
    drifted = {path: value for path, value in declared_versions().items() if value != expected}
    for path, value in drifted.items():
        print(f"{path}: version {value} does not match VERSION {expected}")
    print(f"version {expected}: {len(drifted)} drift(s)")
    return 1 if drifted else 0


def apply(value: str) -> int:
    if not SEMVER.match(value):
        print(f"not a version: {value}")
        return 2
    VERSION_FILE.write_text(f"{value}\n", encoding="utf-8")
    for project in PYTHON_PROJECTS:
        subprocess.run(["uv", "version", value, "--no-sync"], cwd=project, check=True)
    subprocess.run(["npm", "version", value, "--no-git-tag-version", "--allow-same-version"], cwd=FRONTEND, check=True)
    return check()


def main(argv: list[str]) -> int:
    match argv:
        case ["check"]:
            return check()
        case ["set", value]:
            return apply(value)
        case _:
            print("usage: version.py check | set <version>")
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
