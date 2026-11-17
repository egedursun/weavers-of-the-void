import ast
import re
from functools import cache
from pathlib import Path

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.domain.enums.economy import CommodityKind

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
WRITERS = ("engine", "tools", "services", "agents")
PLACEHOLDER = re.compile(r"\{[^}]*\}")


@cache
def writer_texts() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for base in WRITERS for path in (SOURCE / base).rglob("*.py")}


@cache
def typed_goods(path: Path) -> frozenset[str]:
    texts = [writer_texts()[path]]
    for node in ast.walk(ast.parse(texts[0])):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("aerona.catalog."):
            home = SOURCE.joinpath(*node.module.split(".")[1:])
            for candidate in (home.with_suffix(".py"), home / "__init__.py"):
                if candidate.exists():
                    texts.append(candidate.read_text(encoding="utf-8"))
    return frozenset(good.name for good in CommodityKind if any(re.search(rf"\.{good.name}\b", text) for text in texts))


def named_goods(spec: IncidentKindSpec) -> list[CommodityKind]:
    words = PLACEHOLDER.sub("", spec.template).lower()
    return [good for good in CommodityKind if re.search(rf"\b{re.escape(good.value.replace('_', ' '))}s?\b", words)]


def untyped_goods(key: str, spec: IncidentKindSpec) -> list[str]:
    facts = {fact.key for fact in spec.facts}
    writers = [path for path, text in writer_texts().items() if f'"{key}"' in text]
    return [
        good.value
        for good in named_goods(spec)
        if good.value not in key and not any(good.value in fact for fact in facts) and not any(good.name in typed_goods(path) for path in writers)
    ]


def test_a_happening_names_only_goods_its_process_moves() -> None:
    found = {key: goods for key, spec in INCIDENT_KINDS.items() if (goods := untyped_goods(key, spec))}
    assert found == {}


def test_a_good_the_process_never_moves_is_caught() -> None:
    spec = INCIDENT_KINDS["mind.famine_aid"]
    borrowed = IncidentKindSpec(**{**spec.__dict__, "template": "{giver} sent {loads:load|loads} of grain to starving {receiver}."})
    assert untyped_goods("mind.famine_aid", borrowed) == ["grain"]
