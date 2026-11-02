import hashlib
import time

from PIL import Image

from aerona_image_worker.backends.base import BackendSpec, ImageBackend
from aerona_image_worker.backends.png import encode_png
from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink
from aerona_image_worker.errors import GenerationFailedError

CHANNEL_MAX = 255


class FakeBackend:
    def __init__(self, spec: BackendSpec) -> None:
        self._spec = spec
        self._loaded = False

    def load(self) -> None:
        time.sleep(self._spec.fake_load_seconds)
        self._loaded = True

    def generate(self, request: GenerationRequest, report: ProgressSink) -> bytes:
        if not self._loaded:
            raise GenerationFailedError("fake backend is not loaded")
        report(EventKind.ENCODING, 0, request.steps)
        if self._spec.fake_failure_prompt and self._spec.fake_failure_prompt in request.prompt:
            raise GenerationFailedError("fake backend refused the prompt")
        for step in range(1, request.steps + 1):
            time.sleep(self._spec.fake_step_seconds)
            report(EventKind.STEP, step, request.steps)
        report(EventKind.DECODING, request.steps, request.steps)
        return encode_png(render_gradient(request))

    def unload(self) -> None:
        self._loaded = False


def render_gradient(request: GenerationRequest) -> Image.Image:
    digest = hashlib.sha256(f"{request.seed}:{request.prompt}".encode()).digest()
    start, end = digest[:3], digest[3:6]
    span = max(1, request.height - 1)
    column = Image.new("RGB", (1, request.height))
    column.putdata([blend(start, end, row / span) for row in range(request.height)])
    return column.resize((request.width, request.height), Image.Resampling.NEAREST)


def blend(start: bytes, end: bytes, ratio: float) -> tuple[int, int, int]:
    red, green, blue = (min(CHANNEL_MAX, round(a + (b - a) * ratio)) for a, b in zip(start, end, strict=True))
    return red, green, blue


def create_backend(spec: BackendSpec) -> ImageBackend:
    return FakeBackend(spec)
