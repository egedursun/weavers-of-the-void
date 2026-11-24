import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_clipped_frames.py"
SPEC = importlib.util.spec_from_file_location("check_clipped_frames", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def test_a_framed_card_that_scrolls_itself_is_caught() -> None:
    assert GUARD.clipped("<Card className='min-w-0 lg:overflow-y-auto'>\n") == [(1, "Card overflow-y-auto")]
    assert GUARD.clipped("<OrnateFrame\n  frame='card'\n  className='overflow-hidden p-4'\n>") == [(1, "OrnateFrame overflow-hidden")]


def test_a_frame_that_scrolls_an_inner_element_passes() -> None:
    assert GUARD.clipped("<Card className='min-w-0'>\n<CardContent className='overflow-y-auto'>") == []


def test_the_frontend_has_no_clipped_frames() -> None:
    assert GUARD.problems() == []
