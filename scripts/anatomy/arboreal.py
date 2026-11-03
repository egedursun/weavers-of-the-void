import math
import re
import sys
from pathlib import Path

from amorphous import catmull, closed_smooth
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH = 300


def mirror(path: str) -> str:
    return re.sub(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", lambda m: f"{WIDTH - float(m.group(1)):g},{m.group(2)}", path)


def flip(point: tuple[float, float]) -> tuple[float, float]:
    return (WIDTH - point[0], point[1])


def tapered(spine: list[tuple[float, float]], widths: list[float], samples: int = 60, cap: float = 1.0) -> str:
    line = catmull(spine, samples)
    knots = catmull([(w, 0) for w in widths], samples)
    left, right = [], []
    for i, (x, y) in enumerate(line):
        a, b = line[max(0, i - 1)], line[min(len(line) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(dx, dy) or 1
        nx, ny = -dy / norm, dx / norm
        w = knots[i][0]
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    end, before = line[-1], line[-3]
    dx, dy = end[0] - before[0], end[1] - before[1]
    norm = math.hypot(dx, dy) or 1
    tip = (end[0] + dx / norm * knots[-1][0] * cap, end[1] + dy / norm * knots[-1][0] * cap)
    start, after = line[0], line[2]
    sx, sy = start[0] - after[0], start[1] - after[1]
    snorm = math.hypot(sx, sy) or 1
    root = (start[0] + sx / snorm * knots[0][0] * 0.35, start[1] + sy / snorm * knots[0][0] * 0.35)
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left)
    path += f" Q{tip[0]:.1f},{tip[1]:.1f} {right[-1][0]:.1f},{right[-1][1]:.1f} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in right[::-1][1:])
    path += f" Q{root[0]:.1f},{root[1]:.1f} {left[0][0]:.1f},{left[0][1]:.1f}"
    return path + " Z"


def clump(cx: float, cy: float, r: float, seed: int) -> str:
    points = []
    for i in range(22):
        theta = i / 22 * 2 * math.pi
        bump = 1 + 0.12 * math.sin(i * 1.7 + seed) + 0.08 * math.sin(i * 3.1 + seed * 2) + (0.1 if i % 3 == 0 else 0)
        points.append((cx + r * bump * math.cos(theta), cy + r * 0.8 * bump * math.sin(theta)))
    return closed_smooth(points)


TRUNK = tapered([(150, 270), (148, 240), (151, 200), (149, 158), (150, 118), (150, 96)], [84, 62, 48, 48, 58, 44], 80, 0.3)
BOUGHS = [
    tapered([(140, 104), (124, 84), (106, 66), (96, 52)], [20, 15, 10, 6], 30, 0.6),
    tapered([(150, 100), (151, 76), (150, 54), (150, 38)], [22, 16, 11, 6], 30, 0.6),
    tapered([(160, 104), (176, 84), (194, 66), (204, 52)], [20, 15, 10, 6], 30, 0.6),
]
LEG = tapered([(136, 250), (126, 268), (116, 286), (106, 300)], [30, 28, 24, 22], 40, 0.4)
TOES = [
    tapered([(108, 300), (88, 306), (64, 309), (44, 308)], [14, 10, 6, 2.4], 24, 1.2),
    tapered([(110, 304), (102, 312), (94, 318)], [11, 7, 2.6], 20, 1.2),
    tapered([(114, 304), (124, 312), (134, 318)], [9, 6, 2.2], 20, 1.2),
    tapered([(104, 296), (88, 294), (74, 298)], [8, 5, 2], 20, 1.2),
]
ARM = tapered([(130, 132), (110, 138), (88, 134), (70, 124), (56, 118)], [22, 17, 13, 9, 6], 50, 0.8)
FINGERS = [
    tapered([(60, 120), (48, 110), (42, 98)], [5, 3.4, 1.6], 16, 1.4),
    tapered([(58, 119), (44, 118), (32, 114)], [5, 3.4, 1.6], 16, 1.4),
    tapered([(60, 121), (50, 130), (44, 140)], [5, 3.4, 1.6], 16, 1.4),
    tapered([(86, 133), (80, 120), (78, 108)], [6, 4, 1.8], 16, 1.4),
]
CLUMPS = [
    (118, 34, 30, 9),
    (184, 34, 30, 10),
    (150, 22, 30, 3),
    (86, 58, 32, 1),
    (214, 58, 32, 2),
    (62, 84, 22, 6),
    (238, 84, 22, 7),
    (118, 72, 28, 4),
    (182, 72, 28, 5),
    (150, 58, 30, 8),
    (100, 92, 18, 11),
    (200, 92, 18, 12),
]
FACE = "M128,140 C132,128 168,128 172,140 C176,156 172,172 164,180 C156,186 144,186 136,180 C128,172 124,156 128,140 Z"
CORE = "M150,196 C156,196 159,212 159,228 C159,244 156,256 150,256 C144,256 141,244 141,228 C141,212 144,196 150,196 Z"
PODS = " ".join(ellipse(x, y, rx, ry) for x, y, rx, ry in ((214, 152, 4.6, 7), (224, 158, 4.2, 6.4), (233, 150, 3.8, 6)))
POD_STEMS = "M214,145 L212,136 M224,151 L220,138 M233,144 L228,134"
BARK = [
    "M136,262 C134,240 138,214 136,192",
    "M146,268 C144,244 146,220 145,196",
    "M158,266 C160,240 156,214 160,190",
    "M166,258 C166,236 162,214 166,196",
    "M136,190 C134,176 132,164 133,150",
    "M118,136 C104,138 92,136 80,130",
    "M138,98 C128,88 118,76 108,66",
    "M151,94 C151,80 151,66 151,52",
]
FACE_LINES = [
    "M131,148 C136,140 143,139 148,144",
    "M152,144 C157,139 164,140 169,148",
    "M150,148 C148,156 147,162 150,166",
    "M139,172 L144,170 L150,173 L156,169 L161,172",
    "M134,158 C132,164 132,170 134,176",
    "M166,158 C168,164 168,170 166,176",
]


def leaves() -> str:
    marks = []
    for cx, cy, r, seed in CLUMPS:
        for k in range(int(r / 3)):
            angle = k * 2.399 + seed
            dist = r * 0.62 * math.sqrt((k + 0.5) / (r / 3))
            x, y = cx + dist * math.cos(angle), cy + dist * 0.8 * math.sin(angle)
            tilt = angle * 57.3 % 180
            marks.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="2.6" ry="1.1" transform="rotate({tilt:.0f} {x:.1f} {y:.1f})"/>')
    return f'<g fill="{C["green"]}" fill-opacity="0.16">{"".join(marks)}</g>'


def arboreal(states: dict[str, str]) -> Plan:
    torso = " | ".join((*BOUGHS, TRUNK))
    roots = " | ".join((*TOES, LEG, *(mirror(toe) for toe in TOES), mirror(LEG)))
    crown = " | ".join(clump(*item) for item in CLUMPS)
    parts = [
        Part("roots", "Roots", roots, (104, 300)),
        Part("torso", "Trunk", torso, (170, 226)),
        Part("right_branch", "Right branch", " ".join((ARM, *FINGERS)), (90, 134)),
        Part("left_branch", "Left branch", mirror(" ".join((ARM, *FINGERS))), flip((90, 134))),
        Part("head", "Crown", crown, (150, 16)),
        Part("groin", "Seed pods", PODS, (224, 158)),
        Part("face", "Bark face", FACE, (150, 180), subtle=True),
        Part("core", "Heartwood", CORE, (150, 226), inner=True),
    ]
    details = [*BARK, *(mirror(line) for line in BARK[-3:-2]), *FACE_LINES, POD_STEMS]
    marks = [leaves(), '<path d="M86,40 C104,24 132,14 156,12" fill="none" stroke="#ffffff" stroke-opacity="0.07" stroke-width="2.4" stroke-linecap="round"/>']
    if states.get("face", "unhurt") != "lost":
        for x in (140, 160):
            marks.append(f'<ellipse cx="{x}" cy="151" rx="4.6" ry="3.2" fill="#07080c"/>')
            marks.append(f'<ellipse cx="{x}" cy="151.6" rx="2" ry="1.3" fill="{C["gold"]}" fill-opacity="0.75"/>')
            marks.append(f'<circle cx="{x}" cy="151" r="8" fill="{C["gold"]}" fill-opacity="0.05"/>')
    underlay = (
        '<defs><filter id="tshadow" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        '<ellipse cx="150" cy="314" rx="118" ry="10" fill="#000" opacity="0.5" filter="url(#tshadow)"/>'
    )
    return Plan("Tree-bodied", WIDTH, 326, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {"right_branch": "lost", "head": "festering", "torso": "open", "face": "scarred", "roots": "lasting", "left_branch": "prosthesis"}
    fallen = {"core": "fatal", "torso": "open", "groin": "lost"}
    panels = [
        (
            "Unhurt",
            draw(arboreal({}), {}, scale=1.2),
            "A walking oak. Its crown sees, its bark face speaks, its branches grasp and its rooted legs carry it; the heartwood is its heart and mind.",
        ),
        (
            "Wounded",
            draw(arboreal(wounded), wounded, scale=1.2),
            "A branch hewn off, the crown blighted, the trunk split, the face scarred, roots crippled, a grafted iron branch.",
        ),
        ("Fallen", draw(arboreal(fallen), fallen, scale=1.2), "The heartwood rotted through; the trunk split, its seed pods gone."),
    ]
    (OUT / sys.argv[1]).write_text(page("Tree-bodied", "Ents, dryads' kin, walking groves and every body grown of wood and leaf.", panels), encoding="utf-8")
