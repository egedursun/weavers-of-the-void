from collections.abc import Mapping, Sequence

from aerona.agents.ports import LanguageModel
from aerona.prompts import PromptId, output_model, output_schema, render
from aerona.prompts.contexts.base import PromptContext
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.constraints import Constraint
from aerona.rules.registry import Rules


class OutputMismatchError(TypeError):
    pass


async def ask[T: OutputModel](
    model: LanguageModel,
    rules: Rules,
    *,
    label: str,
    system: tuple[PromptId, PromptContext],
    user: tuple[PromptId, PromptContext],
    output: type[T],
    time_limit: int | None = None,
    constraints: Sequence[Constraint] = (),
    variables: Mapping[str, object] | None = None,
) -> T:
    system_id, system_context = system
    user_id, user_context = user
    if output_model(user_id) is not output:
        raise OutputMismatchError(f"Prompt {user_id} does not produce {output.__name__}.")
    schema = output_schema(user_id, rules, constraints, variables)
    return await model.structured(
        label,
        render(system_id, system_context),
        render(user_id, user_context),
        output=output,
        attempts=rules.fate.model_retries,
        schema=schema,
        timeout_seconds=time_limit,
    )
