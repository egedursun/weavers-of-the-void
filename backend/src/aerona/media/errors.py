from aerona.core.errors import AeronaError, ValidationFailedError


class MediaStoreError(AeronaError):
    status_code = 503


class InvalidMediaKeyError(ValidationFailedError):
    pass
