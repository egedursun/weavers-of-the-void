from typing import Any

from aerona.core.errors import NotFoundError
from aerona.domain.enums.agent import AgentKind
from aerona.prompts import PROMPTS, PromptId, output_schema, tool_description
from aerona.prompts.catalog import PromptSpec
from aerona.prompts.environment import TEMPLATE_ROOT
from aerona.prompts.ids import PromptArea
from aerona.rules.registry import Rules
from aerona.services.prompt_preview.models import PromptCatalogue, PromptDetail, PromptEntry, PromptVariable, ToolEntry
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs

NO_PROMPT = "No such prompt."


def type_name(annotation: object) -> str:
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def entry_of(spec: PromptSpec, rules: Rules) -> PromptEntry:
    return PromptEntry(
        prompt_id=spec.prompt_id,
        area=spec.area,
        template_path=spec.template_path,
        context=spec.context.__name__,
        variables=[
            PromptVariable(name=name, type=type_name(field.annotation), required=field.is_required()) for name, field in spec.context.model_fields.items()
        ],
        output=spec.output.__name__ if spec.output is not None else None,
        has_constraints=bool(spec.constraints(rules)),
    )


def tool_entry(spec: ToolSpec[Any, Any], rules: Rules) -> ToolEntry:
    minimum = spec.meta.minimum_rarity(rules)
    return ToolEntry(
        tool_id=spec.tool_id,
        agent=spec.agent,
        description=tool_description(spec.tool_id, rules),
        read_only=spec.meta.read_only,
        action_cost=spec.meta.actions(rules),
        essence_cost=spec.meta.essence(rules),
        minimum_rarity=minimum.value if minimum is not None else None,
        long_job=spec.meta.long_job is not None,
        input_schema=spec.input_model.model_json_schema(),
    )


def catalogue(rules: Rules, area: PromptArea | None = None) -> PromptCatalogue:
    prompts = [entry_of(spec, rules) for spec in PROMPTS.values() if area is None or spec.area is area]
    return PromptCatalogue(
        prompts=prompts,
        son_tools=[tool_entry(spec, rules) for spec in son_specs() if spec.agent is AgentKind.SON],
        mortal_tools=[tool_entry(spec, rules) for spec in mortal_specs() if spec.agent is AgentKind.MORTAL],
    )


def detail(prompt_id: PromptId, rules: Rules) -> PromptDetail:
    spec = PROMPTS.get(prompt_id)
    if spec is None:
        raise NotFoundError(NO_PROMPT)
    source = (TEMPLATE_ROOT / spec.template_path).read_text(encoding="utf-8")
    schema = dict(output_schema(prompt_id, rules)) if spec.output is not None else None
    return PromptDetail(**entry_of(spec, rules).model_dump(), template_source=source, output_schema=schema)
