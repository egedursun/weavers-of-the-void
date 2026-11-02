import time
from multiprocessing.connection import Connection

from aerona_image_worker.backends.base import BackendSpec, ImageBackend
from aerona_image_worker.backends.factory import build_backend
from aerona_image_worker.domain.enums import EventKind
from aerona_image_worker.runtime.messages import Failed, Finished, LoadFailed, ParentMessage, Progress, Ready, Shutdown


def serve(spec: BackendSpec, connection: Connection) -> None:
    started = time.monotonic()
    try:
        backend = build_backend(spec)
        backend.load()
    except Exception as error:
        connection.send(LoadFailed(f"{type(error).__name__}: {error}"))
        return
    connection.send(Ready(load_seconds=time.monotonic() - started))
    serve_requests(backend, connection)


def serve_requests(backend: ImageBackend, connection: Connection) -> None:
    def report(kind: EventKind, step: int, total: int) -> None:
        connection.send(Progress(kind=kind, step=step, total=total))

    while True:
        try:
            message: ParentMessage = connection.recv()
        except EOFError:
            break
        if isinstance(message, Shutdown):
            break
        try:
            connection.send(Finished(image=backend.generate(message.request, report)))
        except Exception as error:
            connection.send(Failed(f"{type(error).__name__}: {error}"))
    backend.unload()
