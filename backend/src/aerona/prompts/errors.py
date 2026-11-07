from aerona.core.grammar import an


class PromptContextMismatchError(TypeError):
    def __init__(self, prompt_id: str, expected: str, given: str) -> None:
        super().__init__(f"Prompt {prompt_id} needs {an(expected)} context, not {given}.")
        self.prompt_id = prompt_id


class PromptOutputMissingError(LookupError):
    def __init__(self, prompt_id: str) -> None:
        super().__init__(f"Prompt {prompt_id} has no structured output.")
        self.prompt_id = prompt_id


class UnknownToolError(LookupError):
    def __init__(self, tool_id: str) -> None:
        super().__init__(f"No model-facing text is defined for tool {tool_id}.")
        self.tool_id = tool_id
