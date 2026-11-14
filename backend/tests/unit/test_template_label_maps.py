import importlib
import pkgutil
import re
from enum import StrEnum
from pathlib import Path

import aerona
import aerona.domain.enums

TEMPLATES = Path(aerona.__file__).resolve().parent / "prompts" / "templates"
LITERAL = re.compile(r"\{%-?\s*set\s+(\w+)\s*=\s*\{(.*?)\}\s*-?%\}", re.DOTALL)
KEY = re.compile(r'^\s*"([a-z_]+)"\s*:', re.MULTILINE)
OLD_GENESIS_LINE = (
    '{% set technology_labels = {"stone": "stone age", "bronze": "bronze age", "iron": "iron age", '
    '"medieval": "middle ages", "renaissance": "renaissance", "steam": "steam and gunpowder"} %}'
)


def enum_kinds() -> list[type[StrEnum]]:
    found: list[type[StrEnum]] = []
    for info in pkgutil.walk_packages(aerona.domain.enums.__path__, "aerona.domain.enums."):
        for value in vars(importlib.import_module(info.name)).values():
            if isinstance(value, type) and issubclass(value, StrEnum) and value is not StrEnum and value not in found:
                found.append(value)
    return found


def gaps_in(where: str, text: str, kinds: list[type[StrEnum]]) -> list[str]:
    gaps = []
    for name, body in LITERAL.findall(text):
        keys = set(KEY.findall(body.replace(", ", ",\n")))
        if len(keys) < 2:
            continue
        for kind in kinds:
            values = {member.value for member in kind}
            if keys <= values and keys != values:
                gaps.append(f"{where}: {name} keys {kind.__name__} but leaves out {sorted(values - keys)}")
    return gaps


def test_a_template_map_keyed_by_an_enum_names_every_value_of_it() -> None:
    kinds = enum_kinds()
    gaps = [gap for path in sorted(TEMPLATES.rglob("*.j2")) for gap in gaps_in(str(path.relative_to(TEMPLATES)), path.read_text(), kinds)]
    assert not gaps, "\n".join(gaps)


def test_the_guard_finds_the_era_map_that_left_the_new_eras_out() -> None:
    assert any("TechnologyEra" in gap and "electrical" in gap for gap in gaps_in("genesis", OLD_GENESIS_LINE, enum_kinds()))
