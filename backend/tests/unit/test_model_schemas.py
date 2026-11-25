from pydantic import BaseModel

from aerona.prompts.contexts.base import OpaqueRules
from aerona.rules.registry import Rules
from tests.source_modules import source_modules


def models() -> set[type[BaseModel]]:
    found: set[type[BaseModel]] = set()
    for module in source_modules():
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__.startswith("aerona."):
                found.add(value)
    return found


def test_no_model_builds_a_schema_for_the_whole_rules_registry() -> None:
    bare = sorted(
        f"{model.__module__}.{model.__name__}.{name}"
        for model in models()
        for name, field in model.model_fields.items()
        if field.annotation is Rules and not any(isinstance(item, OpaqueRules) for item in field.metadata)
    )
    assert bare == [], "fields typed Rules must use RulesSnapshot so the registry's schema is never built:\n" + "\n".join(bare)
