import math
import sys
from pathlib import Path

from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
CX, CY, BASE = 150.0, 128.0, 186.0


def closed_smooth(points: list[tuple[float, float]]) -> str:
    n = len(points)
    path = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = points[i - 1], points[i], points[(i + 1) % n], points[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        path += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return path + " Z"


def blob(cx: float, cy: float, base: float, radius: float, wobble: list[tuple[float, float, float]], *, count: int = 48, flatten: bool = True) -> str:
    points = []
    for i in range(count):
        theta = i / count * 2 * math.pi
        r = radius + sum(a * math.sin(k * theta + phase) for a, k, phase in wobble)
        x, y = cx + r * math.cos(theta), cy + r * 0.82 * math.sin(theta)
        if flatten and y > base:
            x = cx + (x - cx) * (1 + (y - base) / 60)
            y = base + (y - base) * 0.22
        points.append((x, y))
    return closed_smooth(points)


def catmull(points: list[tuple[float, float]], samples: int) -> list[tuple[float, float]]:
    out = []
    padded = [points[0], *points, points[-1]]
    segments = len(points) - 1
    for index in range(samples + 1):
        u = index / samples * segments
        seg = min(int(u), segments - 1)
        t = u - seg
        p0, p1, p2, p3 = padded[seg], padded[seg + 1], padded[seg + 2], padded[seg + 3]
        out.append(
            tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t**3)
                for j in range(2)
            )
        )
    return out


def tendril(spine: list[tuple[float, float]], root: float, tip: float, knob: float) -> str:
    line = catmull(spine, 60)
    left, right = [], []
    for i, (x, y) in enumerate(line):
        a = line[max(0, i - 1)]
        b = line[min(len(line) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(dx, dy) or 1
        nx, ny = -dy / norm, dx / norm
        t = i / (len(line) - 1)
        w = root + (tip - root) * t**0.8
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    end, before = line[-1], line[-4]
    dx, dy = end[0] - before[0], end[1] - before[1]
    norm = math.hypot(dx, dy) or 1
    cap = (end[0] + dx / norm * knob * 2.2, end[1] + dy / norm * knob * 2.2)
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left)
    path += f" Q{cap[0]:.1f},{cap[1]:.1f} {right[-1][0]:.1f},{right[-1][1]:.1f}"
    path += " L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in right[::-1][1:])
    return path + " Z"


MASS = closed_smooth(
    [
        (54, 194),
        (60, 176),
        (70, 150),
        (86, 120),
        (108, 94),
        (132, 78),
        (154, 73),
        (178, 79),
        (202, 96),
        (220, 122),
        (232, 150),
        (240, 176),
        (248, 194),
        (226, 200),
        (196, 203),
        (150, 204),
        (104, 203),
        (74, 200),
    ]
)
TENDRILS = [
    tendril([(92, 132), (70, 118), (58, 96), (50, 72), (40, 54)], 22, 6, 4.5),
    tendril([(212, 124), (234, 110), (246, 88), (256, 66), (270, 50)], 20, 6, 4.2),
    tendril([(80, 192), (58, 196), (36, 200), (16, 202)], 14, 5, 3.4),
    tendril([(222, 194), (246, 198), (268, 202), (288, 204)], 14, 5, 3.4),
]
CORE = blob(CX, 146, 999, 22, [(2.4, 3, 0.9), (1.4, 5, 0.2)], count=24, flatten=False)
EYESPOTS = [(134, 94, 5.2), (153, 88, 6.4), (172, 95, 5.2), (143, 106, 3.6), (163, 106, 3.6), (122, 108, 3), (184, 108, 3)]


def circle(x: float, y: float, r: float) -> str:
    return ellipse(round(x, 1), round(y, 1), r, r)


def amorphous(states: dict[str, str]) -> Plan:
    parts = [
        Part("pseudopods", "Pseudopods", " | ".join(TENDRILS), (52, 70)),
        Part("torso", "Mass", MASS, (222, 160)),
        Part("eye", "Sensing skin", " ".join(circle(x, y, r) for x, y, r in EYESPOTS), (153, 88)),
        Part("core", "Core", CORE, (150, 146), inner=True),
    ]
    bubbles = [
        (112, 150, 4),
        (124, 176, 2.6),
        (190, 140, 3.4),
        (182, 172, 2.2),
        (206, 160, 1.8),
        (100, 132, 2),
        (138, 124, 1.6),
        (172, 124, 2.4),
        (92, 184, 2.2),
        (214, 186, 1.6),
    ]
    marks = [
        f'<path d="{circle(x, y, r)}" fill="#ffffff" fill-opacity="0.05" stroke="#ffffff" stroke-opacity="0.12" stroke-width="0.6"/>' for x, y, r in bubbles
    ]
    marks.append('<path d="M96,118 C106,98 124,84 146,79" fill="none" stroke="#ffffff" stroke-opacity="0.1" stroke-width="2.6" stroke-linecap="round"/>')
    marks.append('<path d="M86,140 C88,132 91,126 95,121" fill="none" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1.6" stroke-linecap="round"/>')
    marks.append('<path d="M60,196 C110,206 190,206 244,196" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="3"/>')
    if states.get("eye", "unhurt") not in {"lost", "prosthesis"}:
        marks.extend(
            f'<circle cx="{x}" cy="{y}" r="{r * 0.45:.1f}" fill="{C["gold"]}" fill-opacity="0.6"/><circle cx="{x - r * 0.2:.1f}" cy="{y - r * 0.2:.1f}" r="{r * 0.16:.1f}" fill="#fff" fill-opacity="0.7"/>'
            for x, y, r in EYESPOTS
        )
    if states.get("core", "unhurt") == "unhurt":
        marks.append(
            f'<circle cx="{CX}" cy="146" r="9" fill="{C["gold"]}" fill-opacity="0.12"/><circle cx="{CX + 2}" cy="144" r="3.4" fill="{C["gold"]}" fill-opacity="0.25"/>'
        )
    underlay = (
        '<defs><filter id="oshadow" x="-20%" y="-30%" width="140%" height="170%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        f'<g filter="url(#oshadow)" opacity="0.45" transform="translate(4,8)"><path d="{MASS}" fill="#000"/></g>'
    )
    return Plan("Amorphous", 300, 215, parts, [], marks, underlay)


if __name__ == "__main__":
    wounded = {"pseudopods": "lost", "eye": "festering", "torso": "open"}
    scarred = {"pseudopods": "prosthesis", "eye": "scarred", "torso": "lasting"}
    fallen = {"core": "fatal", "torso": "open"}
    panels = [
        (
            "Unhurt",
            draw(amorphous({}), {}, scale=1.35),
            "A living mass with no fixed form. Its pseudopods, its sensing skin and its core take their own wounds; the core is its heart and mind.",
        ),
        ("Wounded", draw(amorphous(wounded), wounded, scale=1.35), "Pseudopods torn away, the sensing skin festering, the mass split open."),
        ("Fallen", draw(amorphous(fallen), fallen, scale=1.35), "The core burst; the mass runs and does not close again."),
    ]
    (OUT / sys.argv[1]).write_text(page("Amorphous body", "Oozes, slimes, living gels and every body that holds no fixed shape.", panels), encoding="utf-8")
