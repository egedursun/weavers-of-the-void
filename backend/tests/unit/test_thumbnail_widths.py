import re
from pathlib import Path

from aerona.constants.media import THUMBNAIL_WIDTHS

FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src"
WIDTH_LIST = re.compile(r"export const THUMBNAIL_WIDTHS = \[([^\]]*)\] as const")
LOOSE_WIDTH = re.compile(r"function mediaUrl\([^)]*width\??:\s*number")


def test_the_screens_ask_for_exactly_the_widths_the_server_makes() -> None:
    source = (FRONTEND / "features" / "images" / "media.ts").read_text(encoding="utf-8")
    found = WIDTH_LIST.search(source)
    assert found is not None
    assert {int(width) for width in found.group(1).split(",")} == set(THUMBNAIL_WIDTHS)


def test_no_media_helper_takes_an_untyped_width() -> None:
    loose = [
        str(path.relative_to(FRONTEND))
        for path in FRONTEND.rglob("*.ts*")
        if path.is_file() and "generated" not in path.parts and LOOSE_WIDTH.search(re.sub(r"\s+", " ", path.read_text(encoding="utf-8")))
    ]
    assert loose == []
