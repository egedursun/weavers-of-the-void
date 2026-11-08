from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from aerona.core.errors import ConflictError
from aerona.services.books.assets import print_jpeg
from aerona.services.books.pdf import _layout, _worker_environment


def png(mode: str, size: tuple[int, int]) -> bytes:
    output = BytesIO()
    Image.new(mode, size).save(output, format="PNG")
    return output.getvalue()


def test_a_printed_image_is_flattened_to_a_jpeg_and_never_grown() -> None:
    with Image.open(BytesIO(print_jpeg(png("RGBA", (400, 200)), 100))) as wide:
        assert wide.format == "JPEG" and wide.mode == "RGB" and wide.size == (100, 50)
    with Image.open(BytesIO(print_jpeg(png("L", (60, 30)), 100))) as small:
        assert small.mode == "RGB" and small.size == (60, 30)
    with Image.open(BytesIO(print_jpeg(png("P", (50, 50)), 100))) as palette:
        assert palette.mode == "RGB"


def test_the_print_worker_runs_with_the_platform_libraries() -> None:
    environment = _worker_environment()
    assert environment and all(isinstance(value, str) for value in environment.values())


async def test_a_layout_that_cannot_be_set_is_refused_with_its_reason(tmp_path: Path) -> None:
    with pytest.raises(ConflictError):
        await _layout(tmp_path / "missing.html", tmp_path / "out.pdf")
