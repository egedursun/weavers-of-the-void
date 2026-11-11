import importlib
import pkgutil

from pydantic import BaseModel

import aerona

PACKAGES = ("aerona.api", "aerona.services.player", "aerona.tools", "aerona.prompts")


def subclasses(root: type[BaseModel]) -> set[type[BaseModel]]:
    found: set[type[BaseModel]] = set()
    stack = [root]
    while stack:
        for sub in stack.pop().__subclasses__():
            if sub not in found:
                found.add(sub)
                stack.append(sub)
    return found


def test_no_field_of_a_served_or_received_model_shadows_a_model_attribute() -> None:
    for module in pkgutil.walk_packages(aerona.__path__, "aerona."):
        if module.name.startswith(PACKAGES):
            importlib.import_module(module.name)
    shadowed = sorted(
        f"{kind.__module__}.{kind.__name__}.{name}"
        for kind in subclasses(BaseModel)
        if kind.__module__.startswith("aerona.")
        for name in kind.model_fields
        if hasattr(BaseModel, name)
    )
    assert shadowed == []
