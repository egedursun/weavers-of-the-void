import math
import sys
from pathlib import Path

from forms import capsule, teeth
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
SNOUT, PEDUNCLE, MID = 18.0, 292.0, 100.0
GILL = 104.0


def profile(x: float) -> tuple[float, float]:
    u = max(0.0, min(1.0, (x - SNOUT) / (PEDUNCLE - SNOUT)))
    core = u**0.68 * (1 - u) ** 1.0
    peak = 0.405**0.68 * (1 - 0.405) ** 1.0
    shape = core / peak
    top = 39 * shape + 6.5 * u**2.4
    bottom = 36 * shape + 6.5 * u**2.4
    sag = 3 * math.sin(u * math.pi)
    return MID - top + sag * 0.3, MID + bottom + sag * 0.2


def outline(x0: float, x1: float, steps: int = 80) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    xs = [x0 + (x1 - x0) * i / steps for i in range(steps + 1)]
    return [(x, profile(x)[0]) for x in xs], [(x, profile(x)[1]) for x in xs]


def pts(points: list[tuple[float, float]]) -> str:
    return " L".join(f"{x:.1f},{y:.1f}" for x, y in points)


def gill_arc(reverse: bool = False) -> list[tuple[float, float]]:
    top, bottom = profile(GILL)[0], profile(GILL + 2)[1]
    points = []
    for i in range(21):
        t = i / 20
        y = top + (bottom - top) * t
        x = GILL + 12 * math.sin(t * math.pi)
        points.append((x, y))
    return points[::-1] if reverse else points


def head_path() -> str:
    upper, lower = outline(SNOUT, GILL, 60)
    arc = gill_arc()
    return f"M{SNOUT},{MID} L" + pts(upper[1:]) + " L" + pts(arc) + " L" + pts(lower[::-1][:-1]) + " Z"


def body_path() -> str:
    upper, lower = outline(GILL, PEDUNCLE, 90)
    return "M" + pts(gill_arc(reverse=True)) + " L" + pts(upper[1:]) + f" L{PEDUNCLE + 4},{MID - 5} L{PEDUNCLE + 4},{MID + 5} L" + pts(lower[::-1][:-1]) + " Z"


def silhouette() -> str:
    upper, lower = outline(SNOUT, PEDUNCLE, 140)
    return f"M{SNOUT},{MID} L" + pts(upper[1:]) + f" L{PEDUNCLE + 4},{MID - 5} L{PEDUNCLE + 4},{MID + 5} L" + pts(lower[::-1][:-1]) + " Z"


def on_top(x: float) -> float:
    return profile(x)[0]


def on_bottom(x: float) -> float:
    return profile(x)[1]


def dorsal() -> str:
    a, b = 140, 204
    return (
        f"M{a},{on_top(a) + 2:.1f} C{a + 10},{on_top(a) - 22:.1f} {a + 26},{on_top(a) - 44:.1f} {a + 46},{on_top(a) - 50:.1f} "
        f"C{a + 42},{on_top(a) - 36:.1f} {a + 46},{on_top(b) - 14:.1f} {b},{on_top(b) + 2:.1f} Z"
    )


def finlet() -> str:
    a, b = 238, 262
    return f"M{a},{on_top(a) + 1.5:.1f} C{a + 6},{on_top(a) - 10:.1f} {a + 14},{on_top(a) - 16:.1f} {a + 22},{on_top(a) - 17:.1f} C{a + 20},{on_top(b) - 8:.1f} {b - 2},{on_top(b) - 3:.1f} {b},{on_top(b) + 1.5:.1f} Z"


def anal() -> str:
    a, b = 214, 248
    return f"M{a},{on_bottom(a) - 2:.1f} C{a + 8},{on_bottom(a) + 14:.1f} {a + 22},{on_bottom(a) + 26:.1f} {a + 36},{on_bottom(a) + 29:.1f} C{a + 32},{on_bottom(b) + 14:.1f} {b - 2},{on_bottom(b) + 5:.1f} {b},{on_bottom(b) - 1.5:.1f} Z"


def pelvic() -> str:
    a = 150
    return f"M{a},{on_bottom(a) - 2:.1f} C{a + 6},{on_bottom(a) + 10:.1f} {a + 16},{on_bottom(a) + 18:.1f} {a + 28},{on_bottom(a) + 20:.1f} C{a + 22},{on_bottom(a) + 10:.1f} {a + 18},{on_bottom(a) + 4:.1f} {a + 16},{on_bottom(a) - 2:.1f} Z"


TAIL = (
    "M293,94 C304,86 316,70 328,52 C334,44 341,38 348,36 C344,52 338,70 330,86 C327,92 326,96 327,100 "
    "C326,104 327,108 330,114 C338,130 344,148 348,164 C341,162 334,156 328,148 C316,130 304,114 293,106 Z"
)
PECTORAL = "M114,110 C126,113 142,120 160,132 C168,137 174,142 177,146 C166,146 150,141 136,133 C126,127 118,120 114,110 Z"
PECTORAL_FAR = "M120,104 C134,106 150,112 166,122 C172,126 176,130 178,134 C166,133 152,128 140,121 C130,116 123,110 120,104 Z"
EYE = ellipse(50, 90, 7.5, 7.5)
EYE_FAR = "M49,73.8 C52,71.6 57,71.6 60,73.8 C57,75.4 52,75.4 49,73.8 Z"
JAW = "M21,102 C34,106 48,109 62,109 C64,111 64,114 61,116 C48,118 34,115 25,110 C22,108 20.5,105 21,102 Z"
MOUTH = "M19,100 C32,104 46,107 60,108"
HEART = "M118,122 C115,118 110,120 111,125 C112,129 116,132 120,135 C124,132 128,129 129,125 C130,120 125,118 122,122 C121,123 119,123 118,122 Z"
GUT = "M150,104 C170,96 206,98 224,108 C230,117 226,126 214,131 C194,137 166,135 152,126 C144,120 144,110 150,104 Z"
GROIN = "M208,128 C213,126 219,128 220,132 C218,136 213,137 209,136 C206,134 206,130 208,128 Z"
RAYS = [
    "M150,62 C160,48 172,38 184,32",
    "M162,64 C170,52 180,44 190,38",
    "M176,66 C182,56 190,48 198,44",
    "M222,128 C230,138 240,146 248,150",
    "M232,128 C238,136 244,142 250,146",
    "M300,96 C314,80 326,62 340,44",
    "M300,104 C314,120 326,138 340,156",
    "M124,114 C138,122 152,132 166,142",
    "M130,118 C142,126 154,134 168,144",
]


def lattice(clip: str) -> str:
    lines = []
    for k in range(-40, 60):
        x = 100 + k * 6
        lines.append(f"M{x},50 L{x + 110},160")
        lines.append(f"M{x + 110},50 L{x},160")
    return (
        f'<defs><clipPath id="fishclip"><path d="{clip}"/></clipPath>'
        '<linearGradient id="counter" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#000" stop-opacity="0.35"/><stop offset="0.45" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="0.75" stop-color="#ffffff" stop-opacity="0.05"/><stop offset="1" stop-color="#ffffff" stop-opacity="0.09"/></linearGradient></defs>'
        f'<g clip-path="url(#fishclip)"><path d="{" ".join(lines)}" stroke="{C["detail"]}" stroke-width="0.45" stroke-opacity="0.8" fill="none"/>'
        f'<rect x="0" y="40" width="360" height="130" fill="url(#counter)"/></g>'
    )


def organ_y(x: float, depth: float) -> float:
    return MID + (profile(x)[1] - MID) * depth


def organ(x: float, depth: float, rx: float, ry: float) -> str:
    cy = organ_y(x, depth)
    if ry < 1:
        ry = (profile(x)[1] - MID) * ry
    return ellipse(x, round(cy, 1), rx, round(ry, 1))


def aquatic(states: dict[str, str]) -> Plan:
    body = body_path()
    torso = " | ".join((dorsal(), finlet(), anal(), body))
    parts = [
        Part("right_fin", "Right fin", PECTORAL_FAR, (164, 128), far=True),
        Part("tail", "Tail fin", TAIL, (334, 100)),
        Part("torso", "Body", torso, (210, 84)),
        Part("head", "Head", head_path(), (76, 78)),
        Part("gills", "Gills", "M101,70 C113,86 114,116 103,132 C109,116 109,88 101,70 Z", (108, 100)),
        Part("jaw", "Jaws", JAW, (44, 112), subtle=True),
        Part("left_eye", "Left eye", EYE, (50, 90)),
        Part("right_eye", "Right eye", EYE_FAR, (54.5, 73.8), far=True),
        Part("left_fin", "Left fin", PECTORAL, (150, 134)),
        Part("heart", "Heart", organ(122, 0.5, 7, 6), (122, organ_y(122, 0.5)), inner=True),
        Part("gut", "Gut", organ(184, 0.3, 36, 0.5), (184, organ_y(184, 0.3)), inner=True),
        Part("groin", "Vent", organ(222, 0.72, 5, 4), (222, organ_y(222, 0.72)), inner=True),
        Part("teeth", "Teeth", teeth(40, 108.6, 18, 2.6, 8), (40, 108.6), inner=True, subtle=True),
        Part("spine", "Spine", capsule([(x, profile(x)[0] + (profile(x)[1] - profile(x)[0]) * 0.36) for x in (110, 150, 190, 230, 270, 290)], 4.2), (190, profile(190)[0] + (profile(190)[1] - profile(190)[0]) * 0.36), inner=True, subtle=True),
    ]
    lateral = "M108,98 C150,95 200,96 250,98 C270,99 284,99 296,100"
    details = [lateral, MOUTH, *RAYS]
    marks = [lattice(silhouette())]
    if states.get("left_eye", "unhurt") not in {"lost", "prosthesis"}:
        marks.append(
            f'<circle cx="50" cy="90" r="4.6" fill="{C["gold"]}" fill-opacity="0.6"/><circle cx="50" cy="90" r="2.4" fill="#07080c"/>'
            '<circle cx="48.2" cy="88.2" r="1" fill="#ffffff" fill-opacity="0.8"/>'
        )
    underlay = (
        '<defs><filter id="fshadow" x="-20%" y="-30%" width="140%" height="180%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        f'<g filter="url(#fshadow)" opacity="0.5" transform="translate(5,14)"><path d="{silhouette()} {TAIL}" fill="#000"/></g>'
    )
    return Plan("Aquatic", 360, 190, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "tail": "lost",
        "left_eye": "festering",
        "torso": "open",
        "gills": "scarred",
        "jaw": "lasting",
        "left_fin": "prosthesis",
    }
    fallen = {"heart": "fatal", "head": "open", "right_fin": "lost"}
    panels = [
        (
            "Unhurt",
            draw(aquatic({}), {}, scale=1.15),
            "Seen from its left side. Gills, both fins and both eyes take their own wounds; the far fin and eye sit darker behind.",
        ),
        (
            "Wounded",
            draw(aquatic(wounded), wounded, scale=1.15),
            "Tail fin torn away, an eye festering, the body opened, gills scarred, jaws crooked for good, a silver fin.",
        ),
        ("Fallen", draw(aquatic(fallen), fallen, scale=1.15), "Pierced through the heart; the head split, a fin lost."),
    ]
    (OUT / sys.argv[1]).write_text(page("Aquatic body", "Fish-folk, deep hunters and every body that breathes through gills.", panels), encoding="utf-8")
