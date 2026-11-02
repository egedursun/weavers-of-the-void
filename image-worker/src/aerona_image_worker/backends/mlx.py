import sys
from typing import Any

import mlx.core as mx
from mflux.models.z_image.cli.z_image_turbo_generate import ZImageTurboCommand, build_parser

from aerona_image_worker.backends.base import BackendSpec, ImageBackend
from aerona_image_worker.backends.png import encode_png, snap_dimension
from aerona_image_worker.constants.defaults import SERVICE_NAME
from aerona_image_worker.constants.models import MLX_PROMPT_PLACEHOLDER
from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink
from aerona_image_worker.errors import GenerationFailedError


class StepReporter:
    def __init__(self) -> None:
        self.sink: ProgressSink | None = None

    def call_in_loop(self, *, t: int, latents: Any, config: Any, **_context: Any) -> None:
        mx.eval(latents)
        if self.sink is not None:
            self.sink(EventKind.STEP, t + 1, config.num_inference_steps)

    def call_after_loop(self, *, config: Any, **_context: Any) -> None:
        if self.sink is not None:
            self.sink(EventKind.DECODING, config.num_inference_steps, config.num_inference_steps)


class MlxBackend:
    def __init__(self, spec: BackendSpec) -> None:
        self._spec = spec
        self._model: Any = None
        self._arguments: Any = None
        self._reporter = StepReporter()

    def load(self) -> None:
        self._arguments = parse_arguments(self._spec.model_id)
        self._model = ZImageTurboCommand.load(self._arguments)
        self._model.callbacks.register(self._reporter)

    def generate(self, request: GenerationRequest, report: ProgressSink) -> bytes:
        if self._model is None:
            raise GenerationFailedError("mlx model is not loaded")
        self._arguments.width = snap_dimension(request.width)
        self._arguments.height = snap_dimension(request.height)
        self._arguments.steps = request.steps
        self._reporter.sink = report
        try:
            report(EventKind.ENCODING, 0, request.steps)
            generated = ZImageTurboCommand.generate(self._model, self._arguments, request.seed, request.prompt)
        finally:
            self._reporter.sink = None
        return encode_png(generated.image)

    def unload(self) -> None:
        self._model = None
        self._arguments = None
        mx.clear_cache()


def parse_arguments(model_id: str) -> Any:
    saved = sys.argv
    sys.argv = [SERVICE_NAME, "--model", model_id, "--prompt", MLX_PROMPT_PLACEHOLDER]
    try:
        return build_parser().parse_args()
    finally:
        sys.argv = saved


def create_backend(spec: BackendSpec) -> ImageBackend:
    return MlxBackend(spec)
