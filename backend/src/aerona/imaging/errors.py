from aerona.core.errors import AeronaError


class ImageWorkerError(AeronaError):
    status_code = 502


class ImageGenerationDisabledError(ImageWorkerError):
    status_code = 503


class ImageWorkerUnavailableError(ImageWorkerError):
    status_code = 503


class ImageJobNotFoundError(ImageWorkerError):
    status_code = 404


class ImageJobConflictError(ImageWorkerError):
    status_code = 409


class ImageJobRejectedError(ImageWorkerError):
    status_code = 400


class ImageJobFailedError(ImageWorkerError):
    status_code = 502


class ImageJobCancelledError(ImageWorkerError):
    status_code = 409


class ImageWorkerProtocolError(ImageWorkerError):
    status_code = 502
