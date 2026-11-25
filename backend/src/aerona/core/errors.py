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


class SignedOutError(AeronaError):
    status_code = 401


class PasswordChangeRequiredError(AeronaError):
    status_code = 403


class SetupRequiredError(ConflictError):
    pass


class ForbiddenError(AeronaError):
    status_code = 403

    def __init__(self, message: str, *, permission: str | None = None, role: str | None = None) -> None:
        super().__init__(message)
        self.permission = permission
        self.role = role


class LockedError(AeronaError):
    status_code = 429


class EditConflictError(ConflictError):
    def __init__(self, message: str, changes: list[dict[str, object]]) -> None:
        super().__init__(message)
        self.changes = changes
