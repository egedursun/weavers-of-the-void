import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
SPARE = 3
USED = 4


def lonely() -> int:
    return USED


def wanted() -> int:
    return USED


@router.get("/x")
def routed() -> int:
    return wanted()
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_orphans", REPOSITORY_ROOT / "scripts" / "check_orphans.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_orphans"] = module
    spec.loader.exec_module(module)
    return module


def test_functions_and_constants_nothing_uses_are_found() -> None:
    module = checker()
    found = module.orphans({Path("module.py"): SOURCE}, "")
    assert sorted(item.name for item in found) == ["SPARE", "lonely"]
    assert [item.name for item in module.orphans({Path("module.py"): SOURCE}, "lonely() SPARE")] == []


def test_a_name_that_only_appears_in_a_string_is_still_an_orphan() -> None:
    module = checker()
    spoken = 'LABELS = {"lonely": "Lonely"}\nNAMES = ("SPARE",)\nprint(LABELS, NAMES)\n'
    found = module.orphans({Path("module.py"): SOURCE, Path("labels.py"): spoken}, "")
    assert sorted(item.name for item in found) == ["SPARE", "lonely"]


def test_every_function_and_constant_of_the_backend_is_used() -> None:
    module = checker()
    users = "\n".join(path.read_text(encoding="utf-8") for folder in module.USERS for path in sorted(folder.rglob("*.py")) if path.name != "check_orphans.py")
    assert module.orphans(module.sources(), users) == []
    readers = {path: path.read_text(encoding="utf-8") for folder in module.USERS for path in sorted(folder.rglob("*.py")) if path.name != "check_orphans.py"}
    assert module.unreferenced(module.sources(), readers) == []
    assert module.idle_methods(module.sources(), readers) == []


def test_a_function_whose_name_is_only_shared_by_variables_is_an_orphan(tmp_path: Path) -> None:
    module = checker()
    package = tmp_path / "aerona"
    package.mkdir()
    owner = package / "owners.py"
    owner.write_text("def claim(owner):\n    return owner\n\n\ndef keep(owner):\n    return owner\n", encoding="utf-8")
    other = package / "users.py"
    other.write_text("from aerona.owners import keep\n\n\ndef use(claim):\n    return keep(claim)\n", encoding="utf-8")
    module.SOURCE = package
    files = {path: path.read_text(encoding="utf-8") for path in (owner, other)}
    assert [item.name for item in module.unreferenced(files, {})] == ["claim", "use"]


def test_a_constant_in_a_tuple_assignment_that_nothing_reads_is_an_orphan(tmp_path: Path) -> None:
    module = checker()
    package = tmp_path / "aerona"
    package.mkdir()
    table = package / "table.py"
    table.write_text('USED, SPARE = "used", "spare"\n\n\ndef read():\n    return USED\n', encoding="utf-8")
    reader = package / "reader.py"
    reader.write_text("from aerona.table import read\n\nVALUE = read()\nprint(VALUE)\n", encoding="utf-8")
    module.SOURCE = package
    files = {path: path.read_text(encoding="utf-8") for path in (table, reader)}
    assert [item.name for item in module.unreferenced(files, {})] == ["SPARE"]


def test_a_method_nothing_calls_is_an_orphan_but_a_template_call_counts(tmp_path: Path) -> None:
    module = checker()
    package = tmp_path / "aerona"
    package.mkdir()
    index = package / "index.py"
    index.write_text(
        "class Index:\n    def used(self):\n        return 1\n\n    def idle(self):\n        return 2\n\n    def drawn(self):\n        return 3\n\n"
        "    def __len__(self):\n        return 0\n\n\nclass Typed(int):\n    def framework_hook(self):\n        return 4\n\n\n"
        "def run(index):\n    return index.used()\n",
        encoding="utf-8",
    )
    (package / "page.html.j2").write_text("{{ index.drawn() }}", encoding="utf-8")
    module.SOURCE = package
    assert [item.name for item in module.idle_methods({index: index.read_text(encoding="utf-8")}, {})] == ["Index.idle"]
