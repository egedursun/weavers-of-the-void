import importlib
from typing import cast

from aerona_image_worker.backends.base import BackendFactory, BackendSpec, ImageBackend
from aerona_image_worker.constants.models import BACKEND_MODULES
from aerona_image_worker.settings import Settings


def spec_from_settings(settings: Settings) -> BackendSpec:
    return BackendSpec(
        name=settings.backend,
        model_id=settings.resolved_model_id,
        fake_load_seconds=settings.fake_load_seconds,
        fake_step_seconds=settings.fake_step_seconds,
        fake_failure_prompt=settings.fake_failure_prompt,
    )


def build_backend(spec: BackendSpec) -> ImageBackend:
    module = importlib.import_module(BACKEND_MODULES[spec.name])
    factory = cast(BackendFactory, module.create_backend)
    return factory(spec)
