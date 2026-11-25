class AeronaError(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AeronaError):
    status_code = 404


class ValidationFailedError(AeronaError):
    status_code = 400


class ConflictError(AeronaError):
    status_code = 409


class InsufficientResourcesError(AeronaError):
    status_code = 422


class BusyError(AeronaError):
    status_code = 409


class ReadOnlyError(AeronaError):
    status_code = 423


class UniverseRequiredError(ConflictError):
    pass
