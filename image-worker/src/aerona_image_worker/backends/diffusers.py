from typing import Any

import torch
from diffusers import DiffusionPipeline

from aerona_image_worker.backends.base import BackendSpec, ImageBackend
from aerona_image_worker.backends.png import encode_png, snap_dimension
from aerona_image_worker.constants.models import DIFFUSERS_DEVICE, DIFFUSERS_GUIDANCE_SCALE
from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.domain.generation import GenerationRequest, ProgressSink
from aerona_image_worker.errors import GenerationFailedError


class DiffusersBackend:
    def __init__(self, spec: BackendSpec) -> None:
        self._spec = spec
        self._pipeline: Any = None

    def load(self) -> None:
        self._pipeline = DiffusionPipeline.from_pretrained(self._spec.model_id, torch_dtype=torch.bfloat16).to(DIFFUSERS_DEVICE)

    def generate(self, request: GenerationRequest, report: ProgressSink) -> bytes:
        if self._pipeline is None:
            raise GenerationFailedError("diffusers pipeline is not loaded")
        total = request.steps

        def on_step_end(_pipeline: Any, index: int, _timestep: Any, tensors: dict[str, Any]) -> dict[str, Any]:
            report(EventKind.STEP, index + 1, total)
            if index + 1 == total:
                report(EventKind.DECODING, total, total)
            return tensors

        report(EventKind.ENCODING, 0, total)
        with torch.inference_mode():
            output = self._pipeline(
                prompt=request.prompt,
                width=snap_dimension(request.width),
                height=snap_dimension(request.height),
                num_inference_steps=total,
                guidance_scale=DIFFUSERS_GUIDANCE_SCALE,
                generator=torch.Generator(device=DIFFUSERS_DEVICE).manual_seed(request.seed),
                callback_on_step_end=on_step_end,
            )
        return encode_png(output.images[0])

    def unload(self) -> None:
        self._pipeline = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def create_backend(spec: BackendSpec) -> ImageBackend:
    return DiffusersBackend(spec)
