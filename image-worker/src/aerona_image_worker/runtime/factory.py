from aerona_image_worker.backends.base import BackendSpec
from aerona_image_worker.backends.factory import build_backend
from aerona_image_worker.domain.enums import Isolation
from aerona_image_worker.runtime.base import Runner
from aerona_image_worker.runtime.inline import InlineRunner
from aerona_image_worker.runtime.process import ProcessRunner


def build_runner(spec: BackendSpec, isolation: Isolation) -> Runner:
    if isolation is Isolation.INLINE:
        return InlineRunner(spec, build_backend)
    return ProcessRunner(spec)
