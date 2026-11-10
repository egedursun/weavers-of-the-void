import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_frontend_orphans", REPOSITORY_ROOT / "scripts" / "check_frontend_orphans.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_frontend_orphans"] = module
    spec.loader.exec_module(module)
    return module


def test_an_export_only_its_tests_read_is_an_orphan_unless_it_probes_module_state(tmp_path: Path) -> None:
    module = checker()
    files = {
        tmp_path / "api.ts": "export function useBattleReport(id: number) {\n  return id\n}\nexport function useWar() {\n  return 1\n}\n",
        tmp_path / "view.tsx": "import { useWar } from './api'\nexport function WarView() {\n  return useWar()\n}\n",
        tmp_path / "model.ts": "export function isLost() {\n  return true\n}\n",
        tmp_path / "model.test.ts": "import { isLost, pendingCount } from './model'\nisLost()\npendingCount()\n",
        tmp_path / "gate.ts": "let waiting = 0\nexport function pendingCount() {\n  return waiting\n}\n",
        tmp_path / "shell.tsx": "import { WarView } from './view'\nexport const ROUTES = [WarView]\nexport const MAIN = ROUTES[0]\n",
    }
    assert sorted((orphan.path.name, orphan.name) for orphan in module.orphans_in(files)) == [
        ("api.ts", "useBattleReport"),
        ("model.ts", "isLost"),
        ("shell.tsx", "MAIN"),
    ]


def test_every_frontend_export_is_used_by_the_app() -> None:
    module = checker()
    assert module.orphans_in(module.sources(module.FRONTEND)) == []
