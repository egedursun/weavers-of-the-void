import difflib
import json
import re
from collections.abc import Callable
from pathlib import Path

from amorphous import amorphous
from aquatic import aquatic
from arboreal import arboreal
from avian import avian
from colossal import colossal
from construct import construct
from divine import divine
from humanoid import humanoid
from incorporeal import incorporeal
from insectoid import insectoid
from quadruped import quadruped
from render import DEFS, LOOKS, STATE_LABEL, SWATCH, C, Part, Plan, glyph
from serpentine import serpentine

OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "entity" / "body" / "anatomy"
PLANS: dict[str, Callable[[dict[str, str]], Plan]] = {
    "humanoid": humanoid,
    "quadruped": quadruped,
    "avian": avian,
    "serpentine": serpentine,
    "insectoid": insectoid,
    "aquatic": aquatic,
    "amorphous": amorphous,
    "arboreal": arboreal,
    "incorporeal": incorporeal,
    "colossal": colossal,
    "construct": construct,
    "divine_manifest": divine,
}
STATES = ("open", "festering", "scarred", "lasting", "lost", "prosthesis", "fatal")
TOKENS = {
    C["amber"]: "var(--warning)",
    C["red"]: "var(--destructive)",
    C["crimson"]: "var(--destructive)",
    C["green"]: "var(--success)",
    C["grey"]: "var(--muted-foreground)",
}
PLATE = {C["card"]: "var(--background)"}
PREFIX = "__ID__"
Condition = list[tuple[str, list[str]]]


def tokened(svg: str, tokens: dict[str, str]) -> str:
    for colour, token in tokens.items():
        svg = svg.replace(colour, token)
    return svg


def scoped(svg: str) -> str:
    svg = re.sub(r'\bid="([^"]+)"', rf'id="{PREFIX}\1"', svg)
    return re.sub(r"url\(#([^)]+)\)", rf"url(#{PREFIX}\1)", svg)


def shape_of(plan: Plan) -> tuple[object, ...]:
    parts = tuple((p.key, p.label, p.path, p.anchor, p.inner, p.subtle, p.far, p.prelude, p.tone) for p in plan.parts)
    return (plan.width, plan.height, parts, tuple(plan.details), plan.underlay)


def add(conditions: Condition, key: str, state: str) -> None:
    for part, states in conditions:
        if part == key:
            states.append(state)
            return
    conditions.append((key, [state]))


def marks_of(build: Callable[[dict[str, str]], Plan], base: Plan) -> list[dict[str, object]]:
    hidden: list[Condition] = [[] for _ in base.marks]
    extra: dict[tuple[int, str], Condition] = {}
    for part in base.parts:
        for state in STATES:
            other = build({part.key: state})
            if shape_of(other) != shape_of(base):
                raise ValueError(f"{base.name}: {part.key} {state} changes more than marks")
            matcher = difflib.SequenceMatcher(a=base.marks, b=other.marks, autojunk=False)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag in {"delete", "replace"}:
                    for index in range(i1, i2):
                        add(hidden[index], part.key, state)
                if tag in {"insert", "replace"}:
                    for svg in other.marks[j1:j2]:
                        add(extra.setdefault((i1, svg), []), part.key, state)
    marks: list[dict[str, object]] = []
    for index, svg in enumerate([*base.marks, ""]):
        for (at, shown), conditions in extra.items():
            if at == index:
                marks.append({"svg": scoped(tokened(shown, PLATE)), "show": conditions})
        if index < len(base.marks):
            art = scoped(tokened(svg, PLATE))
            marks.append({"svg": art, "hide": hidden[index]} if hidden[index] else {"svg": art})
    return marks


def export(key: str, build: Callable[[dict[str, str]], Plan]) -> dict[str, object]:
    base = build({})
    return {
        "plan": key,
        "width": base.width,
        "height": base.height,
        "underlay": scoped(tokened(base.underlay, PLATE)),
        "parts": [
            {
                "key": part.key,
                "label": part.label,
                "paths": [piece.strip() for piece in part.path.split("|")],
                "anchor": [round(part.anchor[0], 1), round(part.anchor[1], 1)],
                "inner": part.inner,
                "subtle": part.subtle,
                "far": part.far,
                "tone": part.tone,
                "prelude": scoped(part.prelude),
            }
            for part in base.parts
        ],
        "details": base.details,
        "marks": marks_of(build, base),
    }


def shared() -> dict[str, object]:
    origin = Part("glyph", "", "", (0, 0))
    return {
        "defs": scoped(tokened(" ".join(DEFS.split()), TOKENS)),
        "looks": {look: [{name: scoped(tokened(value, TOKENS)) for name, value in layer.items()} for layer in layers] for look, layers in LOOKS.items()},
        "glyphs": {state: scoped(tokened(glyph(origin, state), TOKENS)) for state in STATES},
        "tones": {state: tokened(colour, TOKENS) for state, (_, colour) in STATE_LABEL.items()},
        "detail": C["detail"],
        "swatch": SWATCH,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "shared.json").write_text(json.dumps(shared(), separators=(",", ":")) + "\n", encoding="utf-8")
    for key, build in PLANS.items():
        data = export(key, build)
        (OUT / f"{key}.json").write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"{key}: {len(data['parts'])} parts, {len(data['marks'])} marks")


if __name__ == "__main__":
    main()
