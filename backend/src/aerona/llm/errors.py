class LlmError(Exception):
    pass


class LlmDisabledError(LlmError):
    pass


class LlmTransientError(LlmError):
    pass


class LlmPermanentError(LlmError):
    pass


class LlmTimeoutError(LlmTransientError):
    pass
