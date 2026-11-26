import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REFUSING_READ = """
NOT_YET = "This place has not been surveyed yet."


@router.get("/places/{place_id}", response_model=View)
async def place(place_id: int) -> View:
    if profile is None:
        raise NotFoundError(NOT_YET)
    raise NotFoundError("No such place.")


@router.get("/maps/{world_id}.jpg", response_class=Response)
async def picture(world_id: int) -> Response:
    raise NotFoundError("This world has no map yet.")


@router.post("/places")
async def make() -> View:
    raise ValidationFailedError("It is not surveyed yet.")
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pending_reads", REPOSITORY_ROOT / "scripts" / "check_pending_reads.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_pending_reads"] = module
    spec.loader.exec_module(module)
    return module


def test_a_read_that_refuses_a_record_not_made_yet_is_caught() -> None:
    assert [(name, text) for name, _line, text in checker().pending_refusals(REFUSING_READ)] == [("place", "This place has not been surveyed yet.")]


def test_no_read_refuses_a_record_that_is_not_made_yet() -> None:
    module = checker()
    assert [problem for path in sorted(module.ROUTERS.rglob("*.py")) for problem in module.pending_refusals(path.read_text(encoding="utf-8"))] == []
