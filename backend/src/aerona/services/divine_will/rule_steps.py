from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from aerona.core.errors import AeronaError
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog, coerce, constraint_violations, with_value
from aerona.services.rule_changes import RuleDesk

RULE_SET = "rule:set"
RULE_RESET = "rule:reset"
RULE_ACTIONS: dict[str, str] = {RULE_SET: "Set a rule of the world", RULE_RESET: "Return a rule of the world to its default"}
KEPT_KEYS = frozenset({"previous", "was_default"})


class RuleStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    namespace: str
    name: str
    value: float | None = None
    previous: float | None = None
    was_default: bool | None = None


def is_rule_step(action_id: str) -> bool:
    return action_id in RULE_ACTIONS


def wanted(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in KEPT_KEYS}


def fitted(where: tuple[int | str, ...], message: str) -> str:
    return f"{'.'.join(str(part) for part in where) or 'input'}: {message}"


def rule_problem(action_id: str, payload: Mapping[str, Any]) -> str:
    try:
        step = RuleStepInput.model_validate(dict(payload))
    except ValidationError as error:
        return f"the input did not fit: {'; '.join(fitted(item['loc'], item['msg']) for item in error.errors(include_url=False))}"
    if not any(item.namespace == step.namespace and item.key == step.name for item in catalog(Rules())):
        return f"there is no rule {step.namespace}.{step.name}; search_rules finds rules by their words"
    if action_id == RULE_SET and step.value is None:
        return "a rule is set to a value; give value, or use rule:reset to return it to its default"
    if action_id == RULE_RESET and step.value is not None:
        return "rule:reset takes no value"
    if step.value is not None:
        try:
            coerce(Rules(), step.namespace, step.name, step.value)
        except AeronaError as error:
            return error.message
    return ""


def refused(text: str) -> dict[str, Any]:
    return {"ok": False, "busy": False, "error": text}


class RuleSteps:
    def __init__(self, desk: RuleDesk) -> None:
        self.desk = desk

    def preview(self, action_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        problem = rule_problem(action_id, payload)
        if problem:
            return refused(problem)
        step = RuleStepInput.model_validate(dict(payload))
        current = self.desk.rules.current
        found = self.desk.find(step.namespace, step.name)
        if found is None:
            return refused(f"there is no rule {step.namespace}.{step.name}")
        target = found.default if step.value is None else coerce(current, step.namespace, step.name, step.value)
        violations = constraint_violations(with_value(current, step.namespace, step.name, target))
        if violations:
            return refused(" ".join(violations))
        return {"ok": True, "busy": False, "error": "", "destructive": False, "costly": False, "essence": 0, "message": ""}

    async def perform(self, action_id: str, payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Any]]:
        step = RuleStepInput.model_validate(wanted(payload))
        before = self.desk.find(step.namespace, step.name)
        if before is None:
            return refused(f"there is no rule {step.namespace}.{step.name}"), dict(payload)
        try:
            after = await self.desk.change(step.namespace, step.name, step.value if action_id == RULE_SET else None)
        except AeronaError as error:
            return refused(error.message), dict(payload)
        kept = {**wanted(payload), "previous": float(before.value), "was_default": before.value == before.default}
        earlier, now = before.value, after.value
        message = f"The rule {step.namespace}.{step.name} changed from {earlier} to {now}."
        return {"ok": True, "error": "", "message": message, "ledger_entry_id": None, "job_id": ""}, kept

    async def undo(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        step = RuleStepInput.model_validate(dict(payload))
        if step.previous is None:
            return refused("this rule step kept no earlier value to return to")
        try:
            await self.desk.change(step.namespace, step.name, None if step.was_default else step.previous)
        except AeronaError as error:
            return refused(error.message)
        return {"ok": True, "error": "", "applied": [f"{step.namespace}.{step.name}"], "conflicts": []}
