import io

from PIL import Image

from aerona_image_worker.constants.limits import DIMENSION_MULTIPLE
from aerona_image_worker.constants.models import PNG_FORMAT


def encode_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=PNG_FORMAT)
    return buffer.getvalue()


def snap_dimension(value: int) -> int:
    return max(DIMENSION_MULTIPLE, value - value % DIMENSION_MULTIPLE)
