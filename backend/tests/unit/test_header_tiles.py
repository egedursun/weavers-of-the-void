import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_header_tiles", REPOSITORY_ROOT / "scripts" / "check_header_tiles.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_header_tiles"] = module
    spec.loader.exec_module(module)
    return module


def test_a_framed_tile_among_header_actions_is_caught() -> None:
    code = (
        "<Section\n"
        "  actions={\n"
        "    <div className='flex'>\n"
        "      <FieldTile id='only-unread' label='Only unread'>\n"
        "        <Switch id='only-unread' />\n"
        "      </FieldTile>\n"
        "    </div>\n"
        "  }\n"
        "/>\n"
        "<Section actions={<FieldTile framed={false} label='Up to'><Input /></FieldTile>} />\n"
        "<FieldTile label='Body'><Input /></FieldTile>\n"
    )
    assert checker().framed_in_actions(code) == [2]


def test_no_header_puts_a_framed_tile_among_its_actions() -> None:
    assert checker().problems() == []
