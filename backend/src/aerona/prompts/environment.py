from functools import cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

from aerona.prompts.filters import FILTERS, GLOBALS

TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"
TEMPLATE_SUFFIX = ".md.j2"


@cache
def environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_ROOT),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
        autoescape=False,
    )
    env.filters.update(FILTERS)
    env.globals.update(GLOBALS)
    return env


def template(path: str) -> Template:
    return environment().get_template(path)


@cache
def string_template(source: str) -> Template:
    return environment().from_string(source)


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().split("\n"))
