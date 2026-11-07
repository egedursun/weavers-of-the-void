from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import core_schema

from aerona.domain.enums.world import LoreLanguage
from aerona.rules.registry import Rules


class OpaqueRules:
    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(Rules, serialization=core_schema.plain_serializer_function_ser_schema(lambda _: None))


RulesSnapshot = Annotated[Rules, OpaqueRules()]


class ContextItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PromptContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def template_variables(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in type(self).model_fields}


class EmptyContext(PromptContext):
    pass


class LoreContext(PromptContext):
    lore_language: LoreLanguage


class RulesContext(PromptContext):
    rules: RulesSnapshot


class LoreRulesContext(LoreContext):
    rules: RulesSnapshot
