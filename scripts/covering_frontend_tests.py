import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SOURCE = FRONTEND / "src"
GENERATED = SOURCE / "api" / "generated"
TEST_SUFFIXES = (".test.ts", ".test.tsx")
IMPORT = re.compile(r"""from\s+['"]([^'"]+)['"]""")
ALIAS = "@/"


def staged_files() -> list[Path]:
    names = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / name for name in names.split() if name.endswith((".ts", ".tsx")) and (ROOT / name).is_relative_to(SOURCE)]


def is_test(path: Path) -> bool:
    return path.name.endswith(TEST_SUFFIXES)


def resolved(test: Path, target: str) -> Path | None:
    if target.startswith(ALIAS):
        base = SOURCE / target.removeprefix(ALIAS)
    elif target.startswith("."):
        base = (test.parent / target).resolve()
    else:
        return None
    for candidate in (base.with_suffix(".ts"), base.with_suffix(".tsx"), base / "index.ts", base / "index.tsx"):
        if candidate.is_file():
            return candidate
    return None


def covering(changed: list[Path]) -> list[Path]:
    sources = {path.resolve() for path in changed if not is_test(path) and not path.is_relative_to(GENERATED)}
    found = {path.resolve() for path in changed if is_test(path) and path.is_file()}
    folders = {path.parent for path in sources}
    for test in sorted(path for path in SOURCE.rglob("*") if is_test(path)):
        if test.parent in folders:
            found.add(test.resolve())
            continue
        imported = {resolved(test, target) for target in IMPORT.findall(test.read_text(encoding="utf-8"))}
        if sources & {path.resolve() for path in imported if path is not None}:
            found.add(test.resolve())
    return sorted(found)


def main() -> int:
    for path in covering(staged_files()):
        print(path.relative_to(FRONTEND))
    return 0


if __name__ == "__main__":
    sys.exit(main())
