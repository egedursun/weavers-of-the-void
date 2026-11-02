class WorkerError(Exception):
    pass


class JobNotFoundError(WorkerError):
    pass


class JobNotCancellableError(WorkerError):
    pass


class ImageNotReadyError(WorkerError):
    pass


class BackendError(WorkerError):
    pass


class LoadTimeoutError(BackendError):
    pass


class ImageTimeoutError(BackendError):
    pass


class GenerationFailedError(BackendError):
    pass


class BackendCrashedError(BackendError):
    pass
