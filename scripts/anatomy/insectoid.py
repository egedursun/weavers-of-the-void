import math
import re
import sys
from pathlib import Path

from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH = 300
HEIGHT = 300


def mirror(path: str) -> str:
    return re.sub(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", lambda m: f"{WIDTH - float(m.group(1)):g},{m.group(2)}", path)


def flip(point: tuple[float, float]) -> tuple[float, float]:
    return (WIDTH - point[0], point[1])


def limb(points: list[tuple[float, float]], widths: list[float]) -> str:
    normals = []
    for index in range(len(points)):
        segs = []
        if index > 0:
            segs.append((points[index - 1], points[index]))
        if index < len(points) - 1:
            segs.append((points[index], points[index + 1]))
        nx = ny = 0.0
        for a, b in segs:
            dx, dy = b[0] - a[0], b[1] - a[1]
            norm = math.hypot(dx, dy) or 1
            nx += -dy / norm
            ny += dx / norm
        norm = math.hypot(nx, ny) or 1
        normals.append((nx / norm, ny / norm))
    left = [(x + nx * w / 2, y + ny * w / 2) for (x, y), (nx, ny), w in zip(points, normals, widths, strict=True)]
    right = [(x - nx * w / 2, y - ny * w / 2) for (x, y), (nx, ny), w in zip(points, normals, widths, strict=True)]
    end, prev = points[-1], points[-2]
    dx, dy = end[0] - prev[0], end[1] - prev[1]
    norm = math.hypot(dx, dy) or 1
    tip = (end[0] + dx / norm * widths[-1] * 1.6, end[1] + dy / norm * widths[-1] * 1.6)
    start, nxt = points[0], points[1]
    dx, dy = start[0] - nxt[0], start[1] - nxt[1]
    norm = math.hypot(dx, dy) or 1
    root = (start[0] + dx / norm * widths[0] * 0.6, start[1] + dy / norm * widths[0] * 0.6)
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left)
    path += f" Q{tip[0]:.1f},{tip[1]:.1f} {right[-1][0]:.1f},{right[-1][1]:.1f}"
    path += " L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in right[::-1][1:])
    path += f" Q{root[0]:.1f},{root[1]:.1f} {left[0][0]:.1f},{left[0][1]:.1f} Z"
    return path


def joints(points: list[tuple[float, float]]) -> str:
    return " ".join(ellipse(round(x, 1), round(y, 1), 1.6, 1.6) for x, y in points[1:-1])


FORELEG = [(136, 100), (108, 92), (96, 62), (104, 40)]
FORELEG_W = [7, 6.5, 5, 2.2]
MIDLEG = [(133, 114), (98, 122), (78, 152), (70, 176)]
MIDLEG_W = [6.5, 6, 4.2, 1.8]
HINDLEG = [(137, 130), (104, 160), (92, 214), (86, 246)]
HINDLEG_W = [7, 6.5, 4.4, 1.8]
CLAW = "M103,40 C100,34 102,28 108,26 C106,30 106,35 108,38 Z"
ANTENNA = [(133, 48), (120, 30), (102, 22), (86, 10)]
ANTENNA_W = [3.2, 2.6, 2.2, 1.2]

HEAD = "M150,42 C164,42 174,50 175,61 C176,72 168,81 150,83 C132,81 124,72 125,61 C126,50 136,42 150,42 Z"
EYE = "M123.5,59 C123.5,50.5 129.5,45.5 136.5,47.5 C139,53.5 138.5,62.5 134,68 C128.5,68 123.5,65 123.5,59 Z"
MANDIBLE = "M140.5,47 C135,41 134,33 139.5,25 C141.5,23 143.5,24 143.2,26.2 C141.2,31 142.2,38 147.5,44 Z"
THORAX = "M150,84 C162,84 170,92 170,104 C170,116 166,128 160,136 L140,136 C134,128 130,116 130,104 C130,92 138,84 150,84 Z"
PETIOLE = "M144.5,133 C146,131 154,131 155.5,133 L156.5,148 C154,150 146,150 143.5,148 Z"
ABDOMEN = (
    "M150,144 C170,144 187,160 189,185 C191,214 181,245 167,265 C161,273 155.5,277 150,277 "
    "C144.5,277 139,273 133,265 C119,245 109,214 111,185 C113,160 130,144 150,144 Z"
)
HEART = "M146.6,154 C146,170 146,198 147,226 C148,229 152,229 153,226 C154,198 154,170 153.4,154 C152,151 148,151 146.6,154 Z"
GUT = "M150,170 C162,170 170,182 170,198 C170,214 162,226 150,226 C138,226 130,214 130,198 C130,182 138,170 150,170 Z"
GROIN = "M150,246 C156,246 160,252 158,258 C156,264 153,267 150,267 C147,267 144,264 142,258 C140,252 144,246 150,246 Z"
DETAILS = [
    "M118,170 C132,178 168,178 182,170",
    "M112,196 C130,206 170,206 188,196",
    "M114,222 C132,232 168,232 186,222",
    "M124,246 C138,254 162,254 176,246",
    "M136,264 C144,268 156,268 164,264",
    "M137,96 C144,100 156,100 163,96",
    "M134,116 C142,120 158,120 166,116",
    "M150,86 L150,134",
    "M142,48 C146,52 154,52 158,48",
    "M150,52 L150,78",
]


def facets(cx: float, cy: float) -> str:
    dots = []
    for row in range(-3, 4):
        for col in range(-2, 3):
            x = cx + col * 2.4 + (1.2 if row % 2 else 0)
            y = cy + row * 2.3
            if (x - cx) ** 2 / 25 + (y - cy) ** 2 / 64 <= 1:
                dots.append(ellipse(round(x, 1), round(y, 1), 0.55, 0.55))
    return " ".join(dots)


def insectoid(states: dict[str, str]) -> Plan:
    parts = [
        Part("right_hindleg", "Right hind leg", limb(HINDLEG, HINDLEG_W), (98, 186)),
        Part("left_hindleg", "Left hind leg", mirror(limb(HINDLEG, HINDLEG_W)), flip((98, 186))),
        Part("right_midleg", "Right middle leg", limb(MIDLEG, MIDLEG_W), (88, 136)),
        Part("left_midleg", "Left middle leg", mirror(limb(MIDLEG, MIDLEG_W)), flip((88, 136))),
        Part("right_foreleg", "Right foreleg", limb(FORELEG, FORELEG_W) + " " + CLAW, (102, 76)),
        Part("left_foreleg", "Left foreleg", mirror(limb(FORELEG, FORELEG_W) + " " + CLAW), flip((102, 76))),
        Part("torso", "Thorax", " | ".join((ABDOMEN, PETIOLE, THORAX)), (176, 206)),
        Part("right_antenna", "Right antenna", limb(ANTENNA, ANTENNA_W), (112, 25)),
        Part("left_antenna", "Left antenna", mirror(limb(ANTENNA, ANTENNA_W)), flip((112, 25))),
        Part("head", "Head", HEAD, (150, 70)),
        Part("jaw", "Mandibles", MANDIBLE + " " + mirror(MANDIBLE), (139, 33)),
        Part("right_eye", "Right compound eye", EYE, (130, 57.5)),
        Part("left_eye", "Left compound eye", mirror(EYE), flip((130, 57.5))),
        Part("heart", "Heart", HEART, (150, 162), inner=True),
        Part("gut", "Gut", GUT, (150, 210), inner=True),
        Part("groin", "Ovipositor", GROIN, (150, 256), inner=True),
    ]
    details = [*DETAILS, joints(FORELEG), mirror(joints(FORELEG)), joints(MIDLEG), mirror(joints(MIDLEG)), joints(HINDLEG), mirror(joints(HINDLEG))]
    marks = [
        '<path d="M150,146 C166,150 178,170 178,196 C178,222 166,252 150,266 C146,250 144,220 144,196 C144,172 146,154 150,146 Z" fill="#ffffff" fill-opacity="0.035"/>'
    ]
    for side, centre in (("right", (130.5, 57.5)), ("left", flip((130.5, 57.5)))):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{facets(*centre)}" fill="{C["gold"]}" fill-opacity="0.35"/>')
    underlay = (
        '<defs><filter id="ishadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter></defs>'
        f'<g filter="url(#ishadow)" opacity="0.5" transform="translate(3,5)"><path d="{ABDOMEN} {THORAX} {HEAD}" fill="#000"/></g>'
    )
    return Plan("Insectoid", WIDTH, HEIGHT, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "right_antenna": "lost",
        "left_eye": "festering",
        "torso": "open",
        "jaw": "scarred",
        "left_midleg": "lasting",
        "right_hindleg": "prosthesis",
    }
    fallen = {"heart": "fatal", "head": "open", "left_foreleg": "lost"}
    panels = [
        (
            "Unhurt",
            draw(insectoid({}), {}, scale=1.3),
            "Seen from above. Two compound eyes, two antennae, mandibles, six jointed legs; the forelegs hook to seize.",
        ),
        (
            "Wounded",
            draw(insectoid(wounded), wounded, scale=1.3),
            "An antenna torn off, an eye festering, the thorax cracked open, mandibles scarred, a leg lamed, a bronze hind leg.",
        ),
        ("Fallen", draw(insectoid(fallen), fallen, scale=1.3), "Its heart burst; the head split, a foreleg torn away."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Insectoid body", "Hive-folk, giant ants and beetles, mantis-kin and every body in a shell of chitin.", panels), encoding="utf-8"
    )
