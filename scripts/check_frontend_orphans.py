import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
EXPORT = re.compile(r"^export (?:async )?(?:function|const|let|class|type|interface|enum) ([A-Za-z_]\w*)", re.M)
MODULE_STATE = re.compile(r"^let ", re.M)
WORD = re.compile(r"[A-Za-z_$][\w$]*")
GENERATED = ("generated", "routeTree.gen.ts")


@dataclass(frozen=True)
class Orphan:
    path: Path
    name: str


def is_test(path: Path) -> bool:
    return ".test." in path.name or "test-utils" in path.parts or "ixtures" in path.name or path.name.startswith("setupTests")


def sources(root: Path) -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.ts*")) if path.is_file() and not any(part in GENERATED for part in path.parts)
    }


def orphans_in(files: dict[Path, str]) -> list[Orphan]:
    counts = {path: Counter(WORD.findall(text)) for path, text in files.items()}
    readers: dict[str, list[Path]] = {}
    for path, words in counts.items():
        for word in words:
            readers.setdefault(word, []).append(path)
    found: list[Orphan] = []
    for path, text in files.items():
        if is_test(path):
            continue
        seams = bool(MODULE_STATE.search(text))
        for name in EXPORT.findall(text):
            if counts[path][name] > 1:
                continue
            others = [other for other in readers.get(name, []) if other != path]
            if any(not is_test(other) for other in others) or (seams and others):
                continue
            found.append(Orphan(path, name))
    return found


def main() -> int:
    found = orphans_in(sources(FRONTEND))
    for orphan in found:
        print(f"{orphan.path.relative_to(ROOT)}: `{orphan.name}` is exported but nothing in the app uses it; wire it in or delete it")
    print(f"frontend orphans: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
