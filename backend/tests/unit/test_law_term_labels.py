import re
from pathlib import Path

from aerona.catalog.laws import LAW_PARAMS

LABELS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "features" / "entity" / "realm" / "labels.ts"


def labelled_terms() -> set[str]:
    text = LABELS.read_text(encoding="utf-8")
    body = text[text.index("export const LAW_PARAMS") :]
    body = body[: body.index("\n}\n")]
    return set(re.findall(r"^  ([a-z_]+):", body, re.M))


def test_every_term_a_law_takes_has_a_label_on_the_screen() -> None:
    terms = {name for spec in LAW_PARAMS.values() for name in spec}
    assert sorted(terms - labelled_terms()) == []
