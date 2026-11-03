import itertools
import math
import re
import sys
from pathlib import Path

from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH = 300
HEIGHT = 300

SPINE = [
    (150, 58),
    (150, 88),
    (132, 118),
    (112, 148),
    (109, 180),
    (130, 205),
    (170, 212),
    (205, 224),
    (218, 252),
    (199, 276),
    (157, 285),
    (117, 277),
    (93, 257),
    (89, 233),
    (101, 215),
]
VENT = 0.74


def catmull(points: list[tuple[float, float]], samples: int = 600) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    padded = [points[0], *points, points[-1]]
    segments = len(points) - 1
    for index in range(samples + 1):
        u = index / samples * segments
        seg = min(int(u), segments - 1)
        t = u - seg
        p0, p1, p2, p3 = padded[seg], padded[seg + 1], padded[seg + 2], padded[seg + 3]
        t2, t3 = t * t, t * t * t
        x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
        y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
        out.append((x, y))
    return out


CURVE = catmull(SPINE)
LENGTHS = [0.0]
for a, b in itertools.pairwise(CURVE):
    LENGTHS.append(LENGTHS[-1] + math.dist(a, b))
TOTAL = LENGTHS[-1]


def at(t: float) -> tuple[tuple[float, float], tuple[float, float]]:
    target = t * TOTAL
    index = next((i for i, length in enumerate(LENGTHS) if length >= target), len(LENGTHS) - 1)
    index = max(1, index)
    a, b = CURVE[index - 1], CURVE[index]
    span = LENGTHS[index] - LENGTHS[index - 1] or 1
    k = (target - LENGTHS[index - 1]) / span
    point = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    dx, dy = b[0] - a[0], b[1] - a[1]
    norm = math.hypot(dx, dy) or 1
    return point, (dx / norm, dy / norm)


def width(t: float) -> float:
    if t < 0.06:
        return 16 + t / 0.06 * 3
    if t < 0.3:
        return 19 + (t - 0.06) / 0.24 * 14
    if t < 0.6:
        return 33
    if t < VENT:
        return 33 - (t - 0.6) / (VENT - 0.6) * 9
    return max(0.8, 24 * (1 - (t - VENT) / (1 - VENT)) ** 1.2)


def band(t0: float, t1: float, scale: float = 1.0, steps: int = 140, cap: bool = False) -> str:
    left, right = [], []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        (x, y), (tx, ty) = at(t)
        half = width(t) * scale / 2
        nx, ny = -ty, tx
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    if not cap:
        points = left + right[::-1]
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points) + " Z"
    (sx, sy), (stx, sty) = at(t0)
    (ex, ey), (etx, ety) = at(t1)
    start_half, end_half = width(t0) * scale / 2, width(t1) * scale / 2
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left)
    path += f" Q{ex + etx * end_half * 1.3:.1f},{ey + ety * end_half * 1.3:.1f} {right[-1][0]:.1f},{right[-1][1]:.1f}"
    path += " L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in right[::-1][1:])
    path += f" Q{sx - stx * start_half * 1.3:.1f},{sy - sty * start_half * 1.3:.1f} {left[0][0]:.1f},{left[0][1]:.1f} Z"
    return path


def diamond(t: float) -> str:
    (x, y), (tx, ty) = at(t)
    nx, ny = -ty, tx
    along, across = width(t) * 0.34, width(t) * 0.26
    pts = [(x + tx * along, y + ty * along), (x + nx * across, y + ny * across), (x - tx * along, y - ty * along), (x - nx * across, y - ny * across)]
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + " Z"


def side_line(offset: float, t0: float, t1: float) -> str:
    pts = []
    for i in range(80):
        t = t0 + (t1 - t0) * i / 79
        (x, y), (tx, ty) = at(t)
        half = width(t) / 2 * offset
        pts.append((x - ty * half, y + tx * half))
    return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)


def mirror_x(path: str) -> str:
    return re.sub(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", lambda m: f"{WIDTH - float(m.group(1)):g},{m.group(2)}", path)


HEAD = (
    "M150,19 C156.5,19 161.5,23 164.5,29.5 C167.5,36 168.5,43 166.5,49 C164.5,55 159.5,59 154,61.5 "
    "L146,61.5 C140.5,59 135.5,55 133.5,49 C131.5,43 132.5,36 135.5,29.5 C138.5,23 143.5,19 150,19 Z"
)
JAW = "M150,19 C156.5,19 161,22.6 163.6,28.4 C159,30.6 154,31.4 150,31.4 C146,31.4 141,30.6 136.4,28.4 C139,22.6 143.5,19 150,19 Z"
EYE = "M133.4,38.6 C134,35.4 137.6,34.4 139.9,36.9 C139.3,40.6 135.4,41.6 133.4,38.6 Z"
PUPIL = "M136.7,35.6 C137.3,37 137.3,39 136.7,40.4 C136.1,39 136.1,37 136.7,35.6 Z"
TONGUE = "M149.1,20 L150.9,20 L150.9,13.5 L154.8,8.4 L153.7,7.5 L150,11.8 L146.3,7.5 L145.2,8.4 L149.1,13.5 Z"
BROW = "M134.5,34 C137.5,31.4 141.5,30.8 144.5,32.2"
NOSTRILS = ellipse(147, 24, 0.9, 0.9) + " " + ellipse(153, 24, 0.9, 0.9)
HEAD_SCALES = [
    "M144.5,35 L150,32.5 L155.5,35 L155.5,45 L150,48.5 L144.5,45 Z",
    "M144.5,35 L139,40 M155.5,35 L161,40",
    "M144.5,45 L140,51 M155.5,45 L160,51",
    "M150,48.5 L150,58",
]


def anchor(t: float) -> tuple[float, float]:
    (x, y), _ = at(t)
    return (round(x, 1), round(y, 1))


def serpentine(states: dict[str, str]) -> Plan:
    parts = [
        Part("torso", "Body", band(0.0, VENT + 0.004), anchor(0.5)),
        Part("tail", "Tail", band(VENT, 1.0), anchor(0.88)),
        Part("head", "Head", HEAD, (150, 52)),
        Part("jaw", "Jaws", JAW, (150, 26), subtle=True),
        Part("right_eye", "Right eye", EYE, (136.7, 38)),
        Part("left_eye", "Left eye", mirror_x(EYE), (WIDTH - 136.7, 38)),
        Part("tongue", "Forked tongue", TONGUE, (150, 13)),
        Part("heart", "Heart", band(0.12, 0.165, 0.5, 30, cap=True), anchor(0.142), inner=True),
        Part("lungs", "Lung", band(0.185, 0.37, 0.42, 60, cap=True), anchor(0.28), inner=True),
        Part("gut", "Gut", band(0.42, 0.68, 0.48, 80, cap=True), anchor(0.55), inner=True),
        Part("groin", "Vent", band(0.703, 0.733, 0.55, 20, cap=True), anchor(0.718), inner=True),
    ]
    details = [side_line(0.62, 0.02, 0.97), side_line(-0.62, 0.02, 0.97), BROW, mirror_x(BROW), *HEAD_SCALES]
    marks = [f'<path d="{diamond(t / 100)}" fill="#000" fill-opacity="0.22" stroke="{C["detail"]}" stroke-width="0.6"/>' for t in range(4, 97, 4)]
    marks.insert(0, f'<path d="{band(0.01, 0.97, 0.34)}" fill="#ffffff" fill-opacity="0.035"/>')
    marks.append(f'<path d="{NOSTRILS}" fill="#0b0c12"/>')
    for side, pupil in (("right", PUPIL), ("left", mirror_x(PUPIL))):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{pupil}" fill="{C["gold"]}" fill-opacity="0.75"/>')
    underlay = (
        '<defs><filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5"/></filter></defs>'
        f'<g filter="url(#shadow)" opacity="0.55" transform="translate(3,5)"><path d="{band(0.0, 1.0)}" fill="#000"/><path d="{HEAD}" fill="#000"/></g>'
    )
    return Plan("Serpentine", WIDTH, HEIGHT, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "tail": "lost",
        "left_eye": "festering",
        "torso": "open",
        "head": "scarred",
        "tongue": "lasting",
        "right_eye": "prosthesis",
    }
    fallen = {"heart": "fatal", "jaw": "open", "torso": "scarred"}
    panels = [
        (
            "Unhurt",
            draw(serpentine({}), {}, scale=1.3),
            "Seen from above as it winds. Both eyes sit on the sides of the head; heart, lung, gut and vent follow the coil inside.",
        ),
        (
            "Wounded",
            draw(serpentine(wounded), wounded, scale=1.3),
            "Tail cut away, an eye festering, the body opened, head scarred, tongue split for good, a glass eye.",
        ),
        ("Fallen", draw(serpentine(fallen), fallen, scale=1.3), "Pierced through the heart; jaws torn, old scars along the body."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Serpentine body", "Serpents, wyrms, nagas' lower halves and every body that moves by its coils.", panels), encoding="utf-8"
    )
