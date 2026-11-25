import importlib
import pkgutil
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import aerona

SOURCE = Path(aerona.__file__).resolve().parent
SKIPPED_MODULES = ("aerona.migration", "aerona.services.books.pdf_worker")
SKIPPED_PACKAGES = frozenset({"alembic"})


def is_skipped(name: str) -> bool:
    return name.startswith(SKIPPED_MODULES) or bool(SKIPPED_PACKAGES & set(name.split(".")))


def source_modules() -> Iterator[ModuleType]:
    for info in pkgutil.walk_packages([str(SOURCE)], "aerona."):
        if not is_skipped(info.name):
            yield importlib.import_module(info.name)
