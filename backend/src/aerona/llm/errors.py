class LlmError(Exception):
    pass


class LlmDisabledError(LlmError):
    pass


class LlmTransientError(LlmError):
    pass


class LlmPermanentError(LlmError):
    pass


class LlmUnavailableError(LlmError):
    pass


class LlmTimeoutError(LlmTransientError):
    pass
