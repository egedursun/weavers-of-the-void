from collections.abc import Callable


def once[F: Callable[..., object]](step: F) -> F:
    return step
