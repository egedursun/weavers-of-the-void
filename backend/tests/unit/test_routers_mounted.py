import importlib
import pkgutil

from aerona.api import routers
from aerona.api.app import ROUTERS


def test_every_router_module_is_mounted_on_the_api() -> None:
    modules = {f"{routers.__name__}.{item.name}" for item in pkgutil.iter_modules(routers.__path__)}
    with_routes = {name for name in modules if hasattr(importlib.import_module(name), "router")}
    assert sorted(with_routes - {module.__name__ for module in ROUTERS}) == []
