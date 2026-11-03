import re
import sys
from pathlib import Path

from human import NAVEL
from humanoid import humanoid
from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent
SHIFT = 40.0
PAIR = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def ramp(value: float, a: float, b: float, lo: float, hi: float) -> float:
    if value <= a:
        return lo
    if value >= b:
        return hi
    t = (value - a) / (b - a)
    t = t * t * (3 - 2 * t)
    return lo + (hi - lo) * t


def vertical(y: float) -> float:
    if y < 60:
        out = 22 + (y - 10) * 0.9
    elif y < 84:
        out = 67 + (y - 60) * 0.5
    else:
        out = 79 + (y - 84)
    if y > 236:
        out = 79 + (236 - 84) + (y - 236) * 0.8
    return out


def scale(y: float) -> float:
    if y < 92:
        return ramp(y, 58, 92, 0.95, 1.55)
    if y < 236:
        return ramp(y, 150, 236, 1.55, 1.38)
    return 1.34


def warp_point(x: float, y: float) -> tuple[float, float]:
    return (100 + (x - 100) * scale(y) + SHIFT, vertical(y))


def warp(path: str) -> str:
    return PAIR.sub(lambda m: "{:.1f},{:.1f}".format(*warp_point(float(m.group(1)), float(m.group(2)))), path)


def colossal(states: dict[str, str]) -> Plan:
    base = humanoid(states)
    parts = [Part(part.key, part.label, warp(part.path), warp_point(*part.anchor), part.inner, part.subtle, part.far) for part in base.parts]
    details = [warp(path) for path in base.details if path != NAVEL]
    details += [
        warp("M72,170 C80,176 88,178 96,176"),
        warp("M128,170 C120,176 112,178 104,176"),
        warp("M44,150 C50,152 56,152 60,148"),
        warp("M156,150 C150,152 144,152 140,148"),
    ]
    marks = []
    for side, x in (("right", 90.8), ("left", 109.2)):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            cx, cy = warp_point(x, 39.5)
            marks.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.8" fill="{C["gold"]}" fill-opacity="0.65"/>')
    navel_x, navel_y = warp_point(100, 178)
    marks.append(f'<ellipse cx="{navel_x:.1f}" cy="{navel_y:.1f}" rx="1.6" ry="2.2" fill="none" stroke="{C["detail"]}" stroke-width="0.8"/>')
    brow = [warp("M83,33.5 C88,30.5 93,30.5 98,32.5"), warp("M117,33.5 C112,30.5 107,30.5 102,32.5")]
    marks.extend(f'<path d="{path}" fill="none" stroke="{C["stroke"]}" stroke-width="1.6" stroke-linecap="round"/>' for path in brow)
    underlay = (
        '<defs><filter id="gshadow" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        '<ellipse cx="140" cy="374" rx="84" ry="7" fill="#000" opacity="0.55" filter="url(#gshadow)"/>'
    )
    return Plan("Colossal", 280, 382, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "right_hand": "lost",
        "left_eye": "lost",
        "left_leg": "festering",
        "torso": "open",
        "left_arm": "scarred",
        "right_foot": "prosthesis",
        "nose": "lasting",
    }
    fallen = {"heart": "fatal", "right_arm": "open", "head": "scarred"}
    panels = [
        (
            "Unhurt",
            draw(colossal({}), {}, scale=1.3),
            "A giant: the same parts as a person, built to another measure. Head sunk between vast shoulders, a barrel chest, stump legs. Blows from smaller foes land low.",
        ),
        (
            "Wounded",
            draw(colossal(wounded), wounded, scale=1.3),
            "A hand lost, an eye gouged, a leg festering, the belly opened, an arm scarred, an iron foot, the nose broken for good.",
        ),
        ("Fallen", draw(colossal(fallen), fallen, scale=1.3), "Felled by a blow to the heart; an arm cut open, old scars on the head."),
    ]
    (OUT / sys.argv[1]).write_text(page("Colossal body", "Giants, ogres, titans' kin and every body built on a greater scale.", panels), encoding="utf-8")
