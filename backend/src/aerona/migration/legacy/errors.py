class MigrationError(Exception):
    pass


class LegacyValidationError(MigrationError):
    pass


class TargetExistsError(MigrationError):
    pass
