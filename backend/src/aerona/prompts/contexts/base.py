from pydantic import BaseModel, ConfigDict, InstanceOf

from aerona.domain.enums.world import LoreLanguage
from aerona.rules.registry import Rules

RulesSnapshot = InstanceOf[Rules]


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
