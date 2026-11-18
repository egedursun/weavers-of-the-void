import importlib
import pkgutil
import re
from pathlib import Path

from sqlalchemy import String, Text

from aerona.db import tables
from aerona.db.base import Base
from aerona.prompts import schemas
from aerona.prompts.schemas.base import OutputModel

assert tables

PERSON = re.compile(
    r"\b(historian|chronicler|author|writer|narrator|storyteller|bard|scribe|speaker|witness|teller|poet|singer|messenger|envoy|keeper|teacher|mentor)s?\b",
    re.IGNORECASE,
)
WHO = re.compile(r"\b(who (they|he|she) (are|is)|their name|name and title|the one who (writes|tells|speaks|sang|wrote))\b", re.IGNORECASE)
SNAPSHOT_REFERENCE = re.compile(r"_(entity|node)_id$")


def output_models() -> list[type[OutputModel]]:
    found: dict[str, type[OutputModel]] = {}
    for info in pkgutil.walk_packages(schemas.__path__, f"{schemas.__name__}."):
        for value in vars(importlib.import_module(info.name)).values():
            if isinstance(value, type) and issubclass(value, OutputModel) and value is not OutputModel:
                found[f"{value.__module__}.{value.__qualname__}"] = value
    return [found[key] for key in sorted(found)]


def invented(model: type[OutputModel]) -> list[str]:
    return [
        f"{model.__name__}.{name}: {(field.description or '')[:90]}"
        for name, field in model.model_fields.items()
        if field.annotation is str and (PERSON.search(name.replace("_", " ")) or WHO.search(field.description or ""))
    ]


def test_no_model_output_invents_a_person_who_is_not_in_the_world() -> None:
    found = [line for model in output_models() for line in invented(model)]
    assert found == [], "a person who writes, tells or speaks must be a mortal the engine chooses, never a name the model makes up: " + "; ".join(found)


def test_a_table_never_keeps_a_person_by_name_alone() -> None:
    found = []
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        references = [column.name for column in table.columns if SNAPSHOT_REFERENCE.search(column.name)]
        for column in table.columns:
            person = PERSON.search(column.name.replace("_", " "))
            if person is None or not isinstance(column.type, (String, Text)) or getattr(column.type, "enum_class", None) is not None:
                continue
            if not any(reference.startswith(person.group(1).lower()) for reference in references):
                found.append(f"{table.name}.{column.name}")
    assert found == [], "keep the person as a link to the mortal (a column ending in _entity_id) beside any name snapshot: " + ", ".join(found)


TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "aerona" / "prompts" / "templates"
TELLER = r"(bard|chronicler|historian|storyteller|narrator|poet|singer|scribe|minstrel|skald)"
INVENTED_TELLER = re.compile(
    rf"\b(an?|some) (mortal |wandering |old |nameless |unnamed )?{TELLER}s?\b|\byou are (the|an?) [^.\n]*\b{TELLER}\b|\bfrom the mouth of\b", re.IGNORECASE
)


def test_no_prompt_tells_through_a_teller_who_is_not_in_the_world() -> None:
    found = [
        f"{path.relative_to(TEMPLATES)}: {match.group(0)}" for path in sorted(TEMPLATES.rglob("*.j2")) for match in INVENTED_TELLER.finditer(path.read_text())
    ]
    assert found == [], "name the mortal who tells it, or tell it with no teller: " + "; ".join(found)
